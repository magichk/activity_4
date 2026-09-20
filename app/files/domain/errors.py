class FileError(Exception):
    """Error de negocio del modulo de ficheros."""


class FileNotFound(FileError):
    def __init__(self, file_id: int):
        super().__init__(f"El fichero {file_id} no existe")


class FileWithoutContent(FileError):
    def __init__(self, file_id: int):
        super().__init__(f"El fichero {file_id} no tiene contenido")


class InvalidPdf(FileError):
    def __init__(self, file_id: int):
        super().__init__(f"El fichero {file_id} no es un PDF valido")


class NotEnoughFilesToMerge(FileError):
    def __init__(self):
        super().__init__("Hacen falta al menos dos ficheros para fusionar")
