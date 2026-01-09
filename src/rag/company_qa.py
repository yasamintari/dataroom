"""
Company-specific Q&A using RAG (Retrieval Augmented Generation).

Enables natural language questions about companies using:
- Databricks Vector Search for retrieval
- Databricks Foundation Models (DBRX, Llama) for generation
- Company-specific context filtering
"""

from typing import List, Dict, Optional
import json


class CompanyQA:
    """Question answering system for company due diligence."""

    def __init__(
        self,
        vector_search_client,
        llm_client,
        index_name: str,
        catalog: str = "yasamin_tari",
        schema: str = "dataroom"
    ):
        """
        Initialize company Q&A system.

        Args:
            vector_search_client: Databricks Vector Search client
            llm_client: LLM client (Databricks Foundation Models)
            index_name: Vector search index name
            catalog: Unity Catalog name
            schema: Schema name
        """
        self.vsc = vector_search_client
        self.llm = llm_client
        self.index_name = index_name
        self.catalog = catalog
        self.schema = schema

        # Get index
        try:
            self.index = self.vsc.get_index(index_name=index_name)
        except Exception as e:
            print(f"Warning: Could not load vector index: {e}")
            self.index = None

    def ask(
        self,
        question: str,
        company_id: str = None,
        top_k: int = 5,
        include_sources: bool = True
    ) -> Dict:
        """
        Ask a question about a company.

        Args:
            question: Natural language question
            company_id: Filter to specific company (optional)
            top_k: Number of relevant chunks to retrieve
            include_sources: Include source documents in response

        Returns:
            Dict with answer, sources, and metadata
        """
        # 1. Retrieve relevant chunks
        relevant_chunks = self.retrieve(question, company_id, top_k)

        if not relevant_chunks:
            return {
                "answer": "I don't have enough information to answer that question based on the available documents.",
                "sources": [],
                "confidence": 0.0
            }

        # 2. Generate answer using LLM
        answer = self.generate_answer(question, relevant_chunks)

        # 3. Compile response
        response = {
            "answer": answer,
            "question": question,
            "company_id": company_id,
            "num_sources": len(relevant_chunks)
        }

        if include_sources:
            response["sources"] = [
                {
                    "document_id": chunk.get("document_id"),
                    "document_type": chunk.get("document_type"),
                    "text": chunk.get("text"),
                    "score": chunk.get("score")
                }
                for chunk in relevant_chunks
            ]

        return response

    def retrieve(
        self,
        query: str,
        company_id: str = None,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant document chunks using vector search.

        Args:
            query: Search query
            company_id: Filter to specific company
            top_k: Number of results to return

        Returns:
            List of relevant chunks with metadata
        """
        if not self.index:
            return []

        try:
            # Build filters
            filters = {}
            if company_id:
                filters["company_id"] = company_id

            # Search vector index
            results = self.index.similarity_search(
                query_text=query,
                columns=["text", "document_id", "document_type", "company_id"],
                filters=filters,
                num_results=top_k
            )

            # Parse results
            chunks = []
            if results and "data_array" in results:
                for row in results["data_array"]:
                    chunks.append({
                        "text": row[0],
                        "document_id": row[1],
                        "document_type": row[2],
                        "company_id": row[3],
                        "score": row[4] if len(row) > 4 else 0.0
                    })

            return chunks

        except Exception as e:
            print(f"Vector search error: {e}")
            return []

    def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict]
    ) -> str:
        """
        Generate answer using LLM with retrieved context.

        Args:
            question: User question
            context_chunks: Retrieved relevant chunks

        Returns:
            Generated answer
        """
        # Build context from chunks
        context = "\n\n".join([
            f"[Document {i+1} - {chunk.get('document_type', 'unknown')}]\n{chunk.get('text', '')}"
            for i, chunk in enumerate(context_chunks)
        ])

        # Build prompt
        prompt = f"""You are a VC due diligence analyst. Answer the following question based ONLY on the provided context from company documents.

Question: {question}

Context from documents:
{context}

Instructions:
- Provide a clear, concise answer based on the context
- If the context doesn't contain enough information, say so
- Cite specific information from the documents when possible
- Be objective and analytical
- Focus on facts, not speculation

Answer:"""

        try:
            # Generate response
            response = self.llm.generate(prompt, max_tokens=500)
            return response.strip()

        except Exception as e:
            return f"Error generating answer: {e}"

    def ask_multiple_companies(
        self,
        question: str,
        company_ids: List[str],
        top_k: int = 5
    ) -> Dict[str, Dict]:
        """
        Ask the same question across multiple companies for comparison.

        Args:
            question: Question to ask
            company_ids: List of company IDs
            top_k: Results per company

        Returns:
            Dict mapping company_id to response
        """
        responses = {}

        for company_id in company_ids:
            response = self.ask(
                question=question,
                company_id=company_id,
                top_k=top_k,
                include_sources=False  # Lighter response for comparison
            )
            responses[company_id] = response

        return responses


class LLMClient:
    """Client for Databricks Foundation Models."""

    def __init__(
        self,
        model_name: str = "databricks-dbrx-instruct",
        endpoint: str = None
    ):
        """
        Initialize LLM client.

        Args:
            model_name: Name of the Databricks Foundation Model
            endpoint: Optional custom endpoint URL
        """
        self.model_name = model_name
        self.endpoint = endpoint

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        try:
            # Use Databricks Foundation Model APIs
            # This is a simplified version - actual implementation depends on your setup

            # Option 1: Using Databricks Model Serving
            if self.endpoint:
                import requests
                import os

                headers = {
                    "Authorization": f"Bearer {os.getenv('DATABRICKS_TOKEN')}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "inputs": [prompt],
                    "parameters": {
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                }

                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    result = response.json()
                    return result["predictions"][0] if "predictions" in result else ""

            # Option 2: Using MLflow AI Gateway (if configured)
            try:
                import mlflow.deployments
                client = mlflow.deployments.get_deploy_client("databricks")

                response = client.predict(
                    endpoint=self.model_name,
                    inputs={
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )

                return response["choices"][0]["text"] if "choices" in response else ""

            except:
                pass

            # Option 3: Direct Foundation Model API call
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

            w = WorkspaceClient()

            response = w.serving_endpoints.query(
                name=self.model_name,
                messages=[ChatMessage(
                    role=ChatMessageRole.USER,
                    content=prompt
                )],
                max_tokens=max_tokens,
                temperature=temperature
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"LLM generation error: {e}")
            return f"Error: Unable to generate response - {e}"


# Convenience function
def create_company_qa_system(
    catalog: str = "yasamin_tari",
    schema: str = "dataroom",
    model_name: str = "databricks-gpt-oss-20b"
) -> CompanyQA:
    """
    Create a company Q&A system.

    Args:
        catalog: Unity Catalog name
        schema: Schema name
        model_name: LLM model name

    Returns:
        CompanyQA instance
    """
    from databricks.vector_search.client import VectorSearchClient

    # Initialize clients
    vsc = VectorSearchClient()
    llm = LLMClient(model_name=model_name)

    # Index name
    index_name = f"{catalog}.{schema}.document_chunks_index"

    # Create QA system
    qa = CompanyQA(
        vector_search_client=vsc,
        llm_client=llm,
        index_name=index_name,
        catalog=catalog,
        schema=schema
    )

    return qa
