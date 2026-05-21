import logging
from typing import Dict, Any, List, Tuple
from fastapi import Depends
from app.services.pinecone import PineconeService
from app.services.google_genai import GoogleGenAIService

logger = logging.getLogger('uvicorn.error')

class ResumeRankingService:
    """Ranks candidates based on their resume embeddings and job description."""
    
    def __init__(self, 
                 pinecone_service: PineconeService = Depends(),
                 genai_service: GoogleGenAIService = Depends()):
        """
        Initialize the candidate ranker.
        
        Args:

            pinecone_index: A Pinecone index reference
        """
        self.pinecone_service = pinecone_service
        self.genai_service = genai_service

        logger.info("Initialized CandidateRanker")
    

    async def get_rankings_pinecone(
            self, 
            job_id: str, 
            job_post_text: str
            ) -> Tuple[Dict[str, List[str]], Dict[str, List[float]]]:

        """
        Get rankings of candidates for a job posting using Pinecone similarity search.
        
        Args:
            job_id: The job ID to filter results
            job_post_text: The text of the job posting
            output_dim: Dimensionality of output embeddings
        
        Returns:
            Tuple containing:
            - Dictionary mapping section names to lists of candidate IDs in rank order
            - Dictionary mapping section names to lists of similarity scores
        """
        try:
            # Generate job posting embedding
            job_post_embeddings = await self.genai_service.fetch_job_text_embeddings(job_post_text)
            
            # Get index statistics
            index_desc = self.pinecone_service.index.describe_index_stats()
            
            # Initialize results dictionaries
            ranks = {}
            scores = {}
            
            # Helper function to extract candidate ID from vector ID
            get_candidate_id = lambda x: x.split('_')[1]
            
            # Query each namespace (resume section)
            for namespace in index_desc['namespaces']:
                logger.info(f"Querying namespace '{namespace}' for job {job_id}")
                
                curr_results = self.pinecone_service.index.query(
                    namespace=namespace,
                    vector=job_post_embeddings,
                    top_k=100,
                    filter={
                        "job_id": {"$eq": job_id}
                    },

                    include_metadata=False,

                    include_values=False
                )
                
                # Extract matches from results

                curr_results = curr_results['matches']
                
                # Extract candidate IDs and scores
                curr_ranks = [get_candidate_id(x['id']) for x in curr_results]
                curr_scores = [x['score'] for x in curr_results]
                
                ranks[namespace] = curr_ranks
                scores[namespace] = curr_scores
                
                logger.info(f"Found {len(curr_ranks)} matches in namespace '{namespace}'")
            
            return ranks, scores

        
        except Exception as e:
            logger.error(f"Error getting rankings from Pinecone: {str(e)}")
            raise
    

    async def weighted_borda_count(self, job_id: str, job_post_text: str, 
                           weights: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate weighted Borda count from multiple ranked lists.
        
        Args:

            job_id: The job ID to filter results

            job_post_text: The text of the job posting
            weights: Dictionary mapping section names to their weights

        
        Returns:

            Dictionary containing:
            - individual_scores: Borda scores for each candidate in each section
            - final_scores: Weighted scores for each candidate
            - final_ranking: List of candidates in descending order of score
        """
        try:
            logger.info(f"Calculating weighted Borda count for job {job_id}")
            
            # Get rankings from Pinecone
            ranks, _ = await self.get_rankings_pinecone(job_id, job_post_text)
            
            # Find all unique candidates
            all_candidates = set()
            for ranking_list in ranks.values():
                all_candidates.update(ranking_list)
            

            logger.info(f"Found {len(all_candidates)} unique candidates")
            
            # Initialize dictionaries to store individual Borda scores and final scores
            individual_scores = {key: {candidate: 0 for candidate in all_candidates} for key in ranks}
            final_scores = {candidate: 0 for candidate in all_candidates}
            
            # Calculate individual Borda scores for each candidate in each ranking list

            for key, ranking_list in ranks.items():
                max_score = len(ranking_list)
                
                # Calculate score for candidates in the list
                for pos, candidate in enumerate(ranking_list):
                    borda_score = max_score - pos
                    individual_scores[key][candidate] = borda_score
                

                # Apply weights and add to final scores
                weight = weights.get(key, 0)
                for candidate in all_candidates:
                    final_scores[candidate] += individual_scores[key][candidate] * weight
            
            # Sort candidates by their final scores in descending order
            final_ranking = sorted(all_candidates, key=lambda c: final_scores[c], reverse=True)
            
            # Prepare the result dictionary
            result = {
                'individual_scores': individual_scores,
                'final_scores': final_scores,
                'final_ranking': final_ranking
            }
            
            logger.info("Successfully calculated weighted Borda count")
            return result
        
        except Exception as e:
            logger.error(f"Error calculating weighted Borda count: {str(e)}")
            raise


