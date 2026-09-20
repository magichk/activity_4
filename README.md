# Activity 4 - Cache con Redis y almacenamiento de objetos con S3

API de un sistema de almacenamiento de ficheros. Parte de la tercera entrega y sustituye dos
piezas de infraestructura por servicios pensados para escalar horizontalmente: las sesiones pasan
de una tabla de Postgres a Redis, y el contenido binario de los ficheros pasa de una columna de la
base de datos a un bucket de S3 (MinIO en local). La arquitectura hexagonal ya establecida en la
entrega anterior es justo lo que permite hacer este cambio sin tocar la logica de negocio.

## Estructura

Cada uno de los dos modulos, `authentication` y `files`, tiene las mismas cuatro capas:

```
app/authentication/
  models.py                definiciones de Tortoise para la base de datos
  api/                     routers y esquemas de entrada y salida
  domain/                  entidades, puertos y logica de negocio
  persistence/             implementaciones de los puertos contra Postgres, Redis o S3
  dependency_injection/    singletons que enlazan la API con el dominio
```

La regla de dependencia sigue siendo la misma: la API conoce al dominio, la persistencia
implementa los puertos que el dominio declara, y el dominio no importa nada de Tortoise, de Redis
ni de boto3. Cambiar de sitio donde se guardan las sesiones o el contenido de los ficheros es
escribir un adaptador nuevo, no reescribir `AuthenticationService` ni `FileService`.

### Lo que evalua esta entrega

El enunciado es explicito: lo que se mide aqui es la implementacion de **servicios completamente
intercambiables a traves de inyeccion de dependencias**, en concreto Redis como cache y S3 como
almacenamiento de objetos. Por eso:

- `SessionRepository` sigue siendo el mismo puerto de la entrega anterior. La implementacion contra
  Postgres (`TortoiseSessionRepository`) se queda en el repositorio, funcional y probada, aunque ya
  no se use: es la prueba de que cambiar de Postgres a Redis en `dependency_injection/container.py`
  es literalmente cambiar una linea.
- El contenido de los ficheros se ha separado de sus metadatos en un puerto nuevo,
  `FileContentStore`, para que `FileService` no sepa si ese contenido vive en S3, en disco o en
  memoria (en los tests, en memoria).

## Redis: cache de sesiones

Cada sesion es una entrada `token -> external_id` con expiracion nativa (`SET ... EX`). Redis borra
la clave solo con el TTL, sin necesidad de un job que purgue sesiones caducadas, y al no guardar
estado en el proceso de la API se pueden levantar varios workers detras de un balanceador sin que
dejen de compartir sesion.

- **Puerto**: `SessionRepository` (`app/authentication/domain/ports.py`), con `set`, `get_external_id`
  y `delete`.
- **Adaptador**: `RedisSessionRepository` (`app/authentication/persistence/redis_repository.py`),
  usando `redis.asyncio`.
- **Inyeccion**: `get_redis_client()` en `app/authentication/dependency_injection/container.py` crea
  un unico cliente por proceso (`lru_cache`) y `get_authentication_service()` lo pasa envuelto en el
  adaptador de Redis.

El perfil de usuario completo (correo, nombre, hash) sigue en Postgres: Redis solo guarda el
puntero minimo para no duplicar datos que ya tienen dueno.

## S3: almacenamiento del contenido de los ficheros

El contenido binario ya no ocupa una columna `BYTEA` en Postgres. Se sube a un bucket de S3
(MinIO en desarrollo) con la clave `files/{id}`, y la API devuelve una URL prefirmada para que el
cliente descargue el fichero directamente del bucket, sin pasar el binario por el servidor.

- **Puerto**: `FileContentStore` (`app/files/domain/ports.py`), con `put`, `get`, `exists`, `delete`
  y `presigned_download_url`.
- **Adaptador**: `S3FileContentStore` (`app/files/persistence/s3_storage.py`), sobre boto3. Como
  boto3 es sincrono, cada llamada va envuelta en `asyncio.to_thread` para no bloquear el event loop
  de FastAPI.
- **Inyeccion**: `get_content_store()` en `app/files/dependency_injection/container.py`, tambien
  como singleton, y `get_file_service()` lo inyecta junto al repositorio de metadatos.

### Por que dos endpoints de S3

`S3FileContentStore` crea dos clientes de boto3, no uno:

- Uno contra el endpoint interno de docker-compose (`http://minio:9000`), que es el que usa la
  propia API para subir, leer y borrar objetos.
- Otro contra el endpoint publico (`http://localhost:9000`), que es el unico que se usa para firmar
  las URLs de descarga.

La firma SigV4 incluye la cabecera `Host` como parte del calculo. Si se firmara una URL con el host
interno `minio:9000`, esa URL seria invalida en cuanto alguien fuera de la red de docker intentara
abrirla, porque el host que ve el navegador no coincidiria con el que se firmo.

## Base de datos

PostgreSQL con Tortoise como ORM. Ahora dos tablas en vez de tres, porque las sesiones han salido
de Postgres:

| Tabla | Contenido |
| --- | --- |
| `users` | clave primaria interna, identificador externo unico, correo, nombre y hash |
| `files` | metadatos del fichero (nombre, descripcion, propietario); el contenido vive en S3 |

### Migraciones

Se gestionan con aerich y estan versionadas en `migrations/`. La migracion de esta entrega elimina
la columna `content` de `files`, ya que ese contenido ha pasado a vivir en S3.

```bash
docker compose --profile tools run --rm make_migrations   # aerich migrate
docker compose --profile tools run --rm migrate           # aerich upgrade
```

Al arrancar, la aplicacion crea las tablas que falten a partir de los modelos y, ademas, se asegura
de que el bucket de S3 exista (MinIO arranca vacio, a diferencia de un bucket de S3 real que ya se
habria creado a mano una vez).

## Endpoints

El token de sesion siempre viaja en la cabecera **`Auth`**.

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| POST | `/authentication/register` | Alta de usuario, devuelve su identificador externo |
| POST | `/authentication/login` | Devuelve el token de sesion (se guarda en Redis con TTL) |
| POST | `/authentication/logout` | Invalida el token recibido |
| GET | `/authentication/introspect` | Valida el token y devuelve el usuario |
| GET | `/files` | Lista los ficheros del usuario |
| POST | `/files` | Crea el fichero con su informacion y devuelve el id |
| GET | `/files/{id}` | Metadatos del fichero y, si hay contenido, su URL de descarga |
| POST | `/files/{id}` | Sube el contenido del fichero a S3 (multipart) |
| DELETE | `/files/{id}` | Borra el fichero y su contenido en S3 |
| POST | `/files/merge` | Fusiona varios PDFs y devuelve el id del resultado |

La creacion sigue partida en dos llamadas a proposito: `POST /files` registra los metadatos y
`POST /files/{id}` sube el contenido binario a S3.

## Decisiones de diseno

- **Redis solo guarda el puntero de sesion.** `token -> external_id`, nada mas. El perfil completo
  se resuelve contra Postgres a partir de ese identificador, para no duplicar datos ni tener que
  invalidar la cache cuando el usuario cambia su nombre.
- **El TTL lo gestiona Redis, no la aplicacion.** `SET ... EX` expira la clave sola; no hace falta un
  cron que borre sesiones caducadas como pasaria con una tabla de Postgres.
- **El contenido del fichero se descarga directo de S3.** La API firma la URL y se aparta: el
  binario nunca pasa por el proceso de FastAPI, que es justo la ventaja de un almacenamiento de
  objetos frente a servir el fichero desde el propio servidor.
- **Dos clientes S3, uno interno y uno publico.** Necesario por como firma SigV4: la cabecera Host
  forma parte de la firma, asi que la URL prefirmada tiene que llevar ya el host que el cliente va a
  usar de verdad.
- **`TortoiseSessionRepository` se queda en el codigo aunque no se use.** Demuestra que el puerto
  `SessionRepository` es intercambiable de verdad: pasar de Postgres a Redis fue cambiar la
  implementacion inyectada, no el contrato del dominio.
- **404 en lugar de 403 para ficheros ajenos.** Con un 403 se estaria confirmando que ese id existe.
- **Singletons con `lru_cache`.** El cliente de Redis y los clientes de boto3 se crean una sola vez
  por proceso, igual que el resto de servicios.

## Codigos de respuesta

| Codigo | Cuando |
| --- | --- |
| 200 | Operacion correcta |
| 400 | Fusion imposible: falta contenido o el PDF no es valido |
| 401 | Credenciales incorrectas o token de sesion no valido (o caducado en Redis) |
| 404 | El fichero no existe o no pertenece al usuario |
| 409 | El correo ya esta registrado |
| 422 | Cuerpo, cabecera `Auth` o lista de ficheros a fusionar mal formados |

## Puesta en marcha

```bash
docker compose up --build api
```

Levanta Postgres, Redis, MinIO y la API. La documentacion swagger queda en
`http://localhost:8000/docs` y la consola de MinIO en `http://localhost:9001` (usuario y contrasena
en `.env`).

Entorno de desarrollo con recarga automatica:

```bash
docker compose --profile dev up --build api-dev
```

## Pruebas

```bash
docker compose --profile dev run --rm api-dev python -m pytest -q
```

- `tests/test_domain.py`: dominio aislado con dobles en memoria para `FileRepository` y
  `FileContentStore`, sin base de datos, Redis ni S3 reales.
- `tests/test_api.py`: la API completa contra Postgres, Redis y S3, incluyendo la descarga real del
  contenido a traves de la URL prefirmada que devuelve la API (no se lee el binario por un atajo
  interno, se pide igual que lo haria un cliente real).

## Formateo del codigo

```bash
docker compose --profile tools run --rm format
```

## Servicios de docker-compose

| Servicio | Para que |
| --- | --- |
| `db` | PostgreSQL 16 con volumen persistente |
| `redis` | Cache de sesiones, sin persistencia a disco |
| `minio` | Almacenamiento de objetos compatible con S3, con volumen persistente |
| `api` | Imagen de produccion |
| `api-dev` | Desarrollo con recarga automatica |
| `make_migrations` | `aerich migrate` |
| `migrate` | `aerich upgrade` |
| `format` | black y ruff |

## Publicacion y CI/CD

- **`.github/workflows/format-check.yml`**: comprueba el formato (black y ruff) en cada pull
  request contra `main`, tal y como pide el enunciado.
- **`.github/workflows/docker-publish.yml`**: construye la imagen de produccion y la publica en
  Docker Hub en cada push a `main`. Necesita dos secrets del repositorio,
  `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` (un access token de Docker Hub, no la contrasena).
