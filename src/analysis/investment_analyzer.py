"""
Investment Analysis Agent for VC Due Diligence.

Analyzes companies across multiple dimensions:
- Market opportunity and size
- Competitive moat and differentiation
- Team quality and experience
- Financial health and metrics
- Product and traction
- Risk factors

Generates investment recommendations and memos.
"""

from typing import Dict, List, Optional
from datetime import datetime
import uuid


class InvestmentAnalyzer:
    """Comprehensive investment analysis for VC due diligence."""

    def __init__(self, qa_system, spark_session, llm_client):
        """
        Initialize investment analyzer.

        Args:
            qa_system: CompanyQA instance for document queries
            spark_session: Spark session for data access
            llm_client: LLM client for analysis generation
        """
        self.qa = qa_system
        self.spark = spark_session
        self.llm = llm_client

        # Analysis dimensions and weights
        self.dimensions = {
            "market_opportunity": {
                "weight": 0.20,
                "questions": [
                    "What is the total addressable market (TAM)?",
                    "What is the market growth rate?",
                    "Who are the target customers?"
                ]
            },
            "competitive_moat": {
                "weight": 0.20,
                "questions": [
                    "What is the company's competitive advantage?",
                    "What are the barriers to entry?",
                    "Who are the main competitors?"
                ]
            },
            "team_quality": {
                "weight": 0.15,
                "questions": [
                    "Who are the founders and what is their background?",
                    "What relevant experience does the team have?",
                    "Who are the key team members?"
                ]
            },
            "financial_health": {
                "weight": 0.15,
                "questions": [
                    "What is the revenue and growth rate?",
                    "What is the burn rate and runway?",
                    "What are the unit economics?"
                ]
            },
            "product_differentiation": {
                "weight": 0.15,
                "questions": [
                    "What makes the product unique?",
                    "What problem does it solve?",
                    "What is the technology or innovation?"
                ]
            },
            "growth_potential": {
                "weight": 0.10,
                "questions": [
                    "What is the customer traction and growth?",
                    "What are the key growth metrics?",
                    "What is the go-to-market strategy?"
                ]
            },
            "risk_factors": {
                "weight": 0.05,
                "questions": [
                    "What are the main risks?",
                    "What regulatory or legal concerns exist?",
                    "What are the execution risks?"
                ]
            }
        }

        # Scoring thresholds
        self.thresholds = {
            "strong_buy": 8.0,
            "buy": 7.0,
            "hold": 5.0,
            "pass": 0.0
        }

    def analyze_company(
        self,
        company_id: str,
        company_name: str = None
    ) -> Dict:
        """
        Perform comprehensive investment analysis of a company.

        Args:
            company_id: Company identifier
            company_name: Company name (optional, for display)

        Returns:
            Complete investment analysis dict
        """
        print(f"\n{'='*60}")
        print(f"Analyzing: {company_name or company_id}")
        print(f"{'='*60}\n")

        # 1. Analyze each dimension
        dimension_scores = []

        for dim_name, dim_config in self.dimensions.items():
            print(f"Analyzing: {dim_name.replace('_', ' ').title()}...")

            score, reasoning, findings = self._analyze_dimension(
                company_id,
                dim_name,
                dim_config["questions"]
            )

            dimension_scores.append({
                "dimension": dim_name,
                "score": score,
                "reasoning": reasoning,
                "key_findings": findings,
                "weight": dim_config["weight"]
            })

        # 2. Calculate overall score
        overall_score = sum(
            dim["score"] * dim["weight"]
            for dim in dimension_scores
        )

        # 3. Generate recommendation
        recommendation = self._determine_recommendation(overall_score)

        # 4. Get financial data
        financial_data = self._get_financial_metrics(company_id)

        # 5. Generate comprehensive analysis
        executive_summary = self._generate_executive_summary(
            company_id,
            dimension_scores,
            overall_score,
            recommendation
        )

        # 6. Generate detailed sections
        market_analysis = self._extract_dimension_text(dimension_scores, "market_opportunity")
        competitive_moat = self._extract_dimension_text(dimension_scores, "competitive_moat")
        team_assessment = self._extract_dimension_text(dimension_scores, "team_quality")
        financial_analysis = self._generate_financial_analysis(financial_data)

        # 7. Extract key risks and opportunities
        key_risks = self._extract_dimension_findings(dimension_scores, "risk_factors")
        key_opportunities = self._extract_opportunities(dimension_scores)

        # 8. Generate recommendations
        next_steps = self._generate_next_steps(dimension_scores, recommendation)

        # 9. Count documents analyzed
        doc_count = self._count_company_documents(company_id)

        # Create analysis record
        analysis = {
            "analysis_id": str(uuid.uuid4()),
            "company_id": company_id,
            "overall_score": overall_score,
            "recommendation": recommendation,
            "confidence_level": self._calculate_confidence(dimension_scores),
            "dimensions": dimension_scores,
            "executive_summary": executive_summary,
            "market_analysis": market_analysis,
            "competitive_moat": competitive_moat,
            "team_assessment": team_assessment,
            "financial_analysis": financial_analysis,
            "key_risks": key_risks,
            "key_opportunities": key_opportunities,
            "next_steps": next_steps,
            "analyzed_at": datetime.utcnow(),
            "analyzed_by": "system",
            "documents_analyzed": doc_count,
            "financial_metrics": financial_data
        }

        print(f"\n{'='*60}")
        print(f"Analysis Complete!")
        print(f"Overall Score: {overall_score:.1f}/10")
        print(f"Recommendation: {recommendation.upper()}")
        print(f"{'='*60}\n")

        return analysis

    def _analyze_dimension(
        self,
        company_id: str,
        dimension_name: str,
        questions: List[str]
    ) -> tuple:
        """
        Analyze a single dimension by asking questions and synthesizing.

        Returns:
            (score, reasoning, key_findings)
        """
        # Ask all questions for this dimension
        answers = []
        for question in questions:
            response = self.qa.ask(question, company_id, top_k=3, include_sources=False)
            answers.append({
                "question": question,
                "answer": response.get("answer", "")
            })

        # Synthesize analysis using LLM
        synthesis_prompt = f"""As a VC analyst, analyze the following information about a company's {dimension_name.replace('_', ' ')}:

{chr(10).join([f"Q: {a['question']}\nA: {a['answer']}\n" for a in answers])}

Provide:
1. A score from 0-10 (where 10 is excellent, 5 is average, 0 is poor)
2. Clear reasoning for the score (2-3 sentences)
3. 2-3 key findings or bullet points

Format your response as JSON:
{{
  "score": <number 0-10>,
  "reasoning": "<explanation>",
  "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"]
}}"""

        try:
            response = self.llm.generate(synthesis_prompt, max_tokens=400)

            # Parse JSON response
            import json
            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            result = json.loads(response.strip())

            return (
                float(result.get("score", 5.0)),
                result.get("reasoning", ""),
                result.get("key_findings", [])
            )

        except Exception as e:
            print(f"  Warning: Analysis error for {dimension_name}: {e}")
            # Return neutral score on error
            return (5.0, "Unable to fully analyze this dimension.", [])

    def _determine_recommendation(self, score: float) -> str:
        """Determine investment recommendation from score."""
        if score >= self.thresholds["strong_buy"]:
            return "strong_buy"
        elif score >= self.thresholds["buy"]:
            return "buy"
        elif score >= self.thresholds["hold"]:
            return "hold"
        else:
            return "pass"

    def _get_financial_metrics(self, company_id: str) -> Dict:
        """Get financial metrics from Delta table."""
        try:
            query = f"""
                SELECT
                    AVG(revenue) as revenue,
                    AVG(revenue_growth_rate) as revenue_growth_rate,
                    AVG(gross_margin) as gross_margin,
                    AVG(burn_rate) as burn_rate,
                    AVG(runway_months) as runway_months,
                    AVG(cac) as cac,
                    AVG(ltv) as ltv,
                    AVG(ltv_cac_ratio) as ltv_cac_ratio,
                    MAX(headcount) as headcount
                FROM {self.qa.catalog}.{self.qa.schema}.financial_metrics
                WHERE company_id = '{company_id}'
            """

            result = self.spark.sql(query).first()

            if result:
                return {
                    "revenue": result.revenue,
                    "revenue_growth_rate": result.revenue_growth_rate,
                    "gross_margin": result.gross_margin,
                    "burn_rate": result.burn_rate,
                    "runway_months": result.runway_months,
                    "cac": result.cac,
                    "ltv": result.ltv,
                    "ltv_cac_ratio": result.ltv_cac_ratio,
                    "headcount": result.headcount
                }

        except:
            pass

        return {}

    def _generate_executive_summary(
        self,
        company_id: str,
        dimensions: List[Dict],
        score: float,
        recommendation: str
    ) -> str:
        """Generate executive summary of the analysis."""
        # Get company info
        company_info = self.qa.ask(
            "What does this company do? Provide a 1-2 sentence overview.",
            company_id,
            top_k=2,
            include_sources=False
        )

        prompt = f"""Write a concise executive summary (3-4 sentences) for this investment analysis:

Company Overview: {company_info.get('answer', 'N/A')}

Overall Score: {score:.1f}/10
Recommendation: {recommendation.upper()}

Key Strengths:
{chr(10).join([f"- {d['dimension']}: {d['score']:.1f}/10" for d in sorted(dimensions, key=lambda x: x['score'], reverse=True)[:3]])}

Write a professional executive summary for the investment memo:"""

        try:
            return self.llm.generate(prompt, max_tokens=200).strip()
        except:
            return f"Investment analysis for {company_id}. Overall score: {score:.1f}/10. Recommendation: {recommendation.upper()}."

    def _extract_dimension_text(self, dimensions: List[Dict], dimension_name: str) -> str:
        """Extract reasoning text for a specific dimension."""
        for dim in dimensions:
            if dim["dimension"] == dimension_name:
                return dim.get("reasoning", "")
        return ""

    def _extract_dimension_findings(self, dimensions: List[Dict], dimension_name: str) -> List[str]:
        """Extract key findings for a specific dimension."""
        for dim in dimensions:
            if dim["dimension"] == dimension_name:
                return dim.get("key_findings", [])
        return []

    def _extract_opportunities(self, dimensions: List[Dict]) -> List[str]:
        """Extract key opportunities from high-scoring dimensions."""
        opportunities = []

        for dim in dimensions:
            if dim["score"] >= 7.0:  # High score = opportunity
                findings = dim.get("key_findings", [])
                opportunities.extend(findings[:2])  # Top 2 findings

        return opportunities[:5]  # Return top 5 opportunities

    def _generate_financial_analysis(self, metrics: Dict) -> str:
        """Generate financial analysis text."""
        if not metrics:
            return "Financial data not available."

        parts = []

        if metrics.get("revenue"):
            parts.append(f"Revenue: ${metrics['revenue']:,.0f}")

        if metrics.get("revenue_growth_rate"):
            parts.append(f"Growth rate: {metrics['revenue_growth_rate']*100:.1f}%")

        if metrics.get("burn_rate") and metrics.get("runway_months"):
            parts.append(f"Burn rate: ${metrics['burn_rate']:,.0f}/month")
            parts.append(f"Runway: {metrics['runway_months']:.1f} months")

        if metrics.get("ltv_cac_ratio"):
            parts.append(f"LTV/CAC: {metrics['ltv_cac_ratio']:.1f}x")

        return ". ".join(parts) + "." if parts else "Limited financial data available."

    def _generate_next_steps(self, dimensions: List[Dict], recommendation: str) -> List[str]:
        """Generate recommended next steps."""
        steps = []

        if recommendation in ["strong_buy", "buy"]:
            steps.append("Schedule founder meeting for deep dive")
            steps.append("Request detailed financial model and projections")

            # Add dimension-specific steps
            for dim in dimensions:
                if dim["score"] < 6.0:  # Low score = need more diligence
                    dim_name = dim["dimension"].replace("_", " ")
                    steps.append(f"Conduct additional diligence on {dim_name}")

            steps.append("Prepare term sheet and valuation analysis")

        elif recommendation == "hold":
            steps.append("Request additional information on key concerns")
            steps.append("Schedule follow-up in 3-6 months")

        else:  # pass
            steps.append("Send polite pass email to founders")

        return steps[:5]  # Max 5 steps

    def _calculate_confidence(self, dimensions: List[Dict]) -> float:
        """Calculate confidence level based on dimension variance."""
        scores = [d["score"] for d in dimensions]
        variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)

        # Lower variance = higher confidence
        confidence = max(0.0, min(1.0, 1.0 - variance / 25.0))
        return confidence

    def _count_company_documents(self, company_id: str) -> int:
        """Count documents for a company."""
        try:
            result = self.spark.sql(f"""
                SELECT COUNT(*) as count
                FROM {self.qa.catalog}.{self.qa.schema}.documents
                WHERE company_id = '{company_id}'
            """).first()

            return result.count if result else 0

        except:
            return 0


# Convenience function
def analyze_company(
    company_id: str,
    qa_system,
    spark_session,
    llm_client
) -> Dict:
    """
    Analyze a company and return investment recommendation.

    Args:
        company_id: Company identifier
        qa_system: CompanyQA instance
        spark_session: Spark session
        llm_client: LLM client

    Returns:
        Investment analysis dict
    """
    analyzer = InvestmentAnalyzer(qa_system, spark_session, llm_client)
    return analyzer.analyze_company(company_id)
