from typing import Optional, Dict
from pinecone import AwsRegion, ServerlessSpec, CloudProvider
from pinecone.grpc import PineconeGRPC
from pinecone.grpc.pinecone import GRPCIndex
from app.models import *
import logging

logger = logging.getLogger('uvicorn.error')

class PineconeService:
    """Manages interactions with Pinecone Vector database"""

    def __init__(self, key: str) -> None:
        """
        Initialize Pinecone client with API key
        """
        self.client = PineconeGRPC(api_key=key)
        logger.info("PineconeGRPC client initialized")
        self.ensure_index_exists("resume-index")
        self.index = self.get_index("resume-index")

    def ensure_index_exists(
            self, 
            index_name: str,
            dimension: int = 768,
            metric: str = "cosine",
            cloud = CloudProvider.AWS,
            region = AwsRegion.US_EAST_1):

        """
        Ensure that the specified index exists, creating it if necessary.
        
        Args:
            index_name: The name of the index to check/create
            dimension: The dimension of the vectors to be stored
            metric: The distance metric to use
            cloud: The cloud provider to use
            region: The region to create the index in
        """
        if not self.client.has_index(index_name):
            logger.info(f"Creating Pinecone index: {index_name}")
            self.client.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,

                spec=ServerlessSpec(
                    cloud=cloud,
                    region=region
                )
            )
            logger.info(f"Successfully created index: {index_name}")
        else:
            logger.info(f"Index {index_name} already exists")

    def get_index(self, index_name: str, host: Optional[str] = None) -> GRPCIndex:
        """
        Get a reference to the specified index.
        
        Args:
            index_name: The name of the index to get
            host: Optional host URL for the index
        
        Returns:
            A reference to the index
        """

        if host:
            return self.client.Index(host=host)
        return self.client.Index(index_name)
            
    def upsert_embeddings(
            self,
            embeddings: Dict[str, List[Dict]],
            batch_size: int = 100) -> None:
        """
        Upsert embeddings to the specified index in batches.
        
        Args:
            index: The Pinecone index to upsert to
            embeddings: A dictionary mapping namespaces to lists of embedding vectors
            batch_size: The number of vectors to upsert in each batch
        """
        for namespace in embeddings:
            namespace_data = embeddings[namespace]
            total_vectors = len(namespace_data)
            logger.info(f"Upserting {total_vectors} vectors to namespace '{namespace}'")
            for i in range(0, total_vectors, batch_size):
                batch = namespace_data[i:i+batch_size]
                try:
                    self.index.upsert(
                        vectors=batch,
                        namespace=namespace
                    )
                    logger.info(f"Upserted batch {i//batch_size + 1}/{(total_vectors-1)//batch_size + 1} "
                               f"to namespace '{namespace}'")
                except Exception as e:
                    logger.error(f"Error upserting batch to namespace '{namespace}': {str(e)}")

