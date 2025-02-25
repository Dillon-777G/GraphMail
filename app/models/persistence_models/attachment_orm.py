from sqlalchemy import Column, Integer, String

from app.persistence.base_connection import Base

from app.config.environment_config import EnvironmentConfig

class DBAttachment(Base):
    __tablename__ = "tbl_email_attachment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, nullable=False)
    url = Column(String(512), nullable=False)
    name = Column(String(250), nullable=False)
    graph_attachment_id = Column(String(250), unique=True, nullable=False)

    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'jpeg', 'webp', 'png', 'jpg'}

    

    def generate_unique_url(self):
        """Generate a unique URL for email attachments
            
        Raises:
            ValueError: If the name doesn't contain a file extension or has an invalid extension
        """
        if '.' not in self.name:
            raise ValueError(f"Invalid attachment name: {self.name}. Name must include a file extension.")
            
        base_name, extension = self.name.rsplit('.', maxsplit=1)
        extension = extension.lower()  # Normalize extension to lowercase
        
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension: .{extension}. Allowed extensions are: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )
            
        unique_suffix = f"{self.email_id}_{self.graph_attachment_id}"
        # self.url = f"{EnvironmentConfig.get('ATTACHMENT_FILE_SYSTEM_PATH')}{base_name}_{unique_suffix}.{extension}"
        self.url = f"{EnvironmentConfig.get('TEST_ATTACHMENT_FILE_SYSTEM_PATH')}{base_name}_{unique_suffix}.{extension}"

    def to_dict(self):
        """Convert the model instance to a dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }