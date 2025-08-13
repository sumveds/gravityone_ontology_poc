from loguru import logger

logger.add("gravityone_ontology.log", rotation="5 MB", level="INFO")