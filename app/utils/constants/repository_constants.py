from dataclasses import dataclass

@dataclass(frozen=True)
class RepositoryConstants:
    """
    Constants for the repository layer.
    """
    MYSQL_DUPLICATE_ENTRY_ERROR = 1062
    
    