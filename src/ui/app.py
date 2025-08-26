"""Streamlit web interface for ConceptDB MVP demo"""

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from typing import List, Dict, Any

# Configuration
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")
API_V1_URL = f"{API_BASE_URL}/api/v1"

# Page configuration
st.set_page_config(
    page_title="ConceptDB - Concept-Type Database",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    .concept-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #fff;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-message {
        color: #4CAF50;
        font-weight: bold;
    }
    .error-message {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def check_api_health():
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.json() if response.status_code == 200 else None
    except:
        return None


def create_concept(name: str, description: str, metadata: Dict = None):
    """Create a new concept via API"""
    try:
        payload = {
            "name": name,
            "description": description,
            "metadata": metadata or {}
        }
        response = requests.post(f"{API_V1_URL}/concepts", json=payload)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Failed to create concept: {e}")
        return None


def search_concepts(query: str, limit: int = 10, threshold: float = 0.7):
    """Search for concepts via API"""
    try:
        payload = {
            "query": query,
            "limit": limit,
            "threshold": threshold
        }
        response = requests.post(f"{API_V1_URL}/search", json=payload)
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Failed to search concepts: {e}")
        return []


def analyze_text(text: str, extract_concepts: bool = True, auto_create: bool = False):
    """Analyze text and extract concepts"""
    try:
        payload = {
            "text": text,
            "extract_concepts": extract_concepts,
            "auto_create": auto_create,
            "max_concepts": 5
        }
        response = requests.post(f"{API_V1_URL}/analyze", json=payload)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Failed to analyze text: {e}")
        return None


def get_all_concepts(page: int = 1, page_size: int = 10):
    """Get all concepts with pagination"""
    try:
        response = requests.get(
            f"{API_V1_URL}/concepts",
            params={"page": page, "page_size": page_size}
        )
        return response.json() if response.status_code == 200 else []
    except Exception as e:
        st.error(f"Failed to get concepts: {e}")
        return []


def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🧠 ConceptDB</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Revolutionary Concept-Type Database - Understanding Meaning, Not Just Storing Vectors</p>', unsafe_allow_html=True)
    
    # Check API health
    health = check_api_health()
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.radio(
            "Select Page",
            ["🏠 Home", "➕ Create Concept", "🔍 Search Concepts", 
             "📊 Analyze Text", "🎯 Customer Insights", "📈 Dashboard"]
        )
        
        st.divider()
        
        # API Status
        st.header("System Status")
        if health:
            st.success(f"✅ API Status: {health['status']}")
            st.info(f"📚 Total Concepts: {health.get('total_concepts', 0)}")
            st.info(f"🔌 Qdrant: {'Connected' if health['qdrant_connected'] else 'Disconnected'}")
            st.info(f"💾 Database: {'Connected' if health['database_connected'] else 'Disconnected'}")
            st.info(f"🤖 Model: {'Loaded' if health['model_loaded'] else 'Not Loaded'}")
        else:
            st.error("❌ API is not responding")
    
    # Main content area
    if page == "🏠 Home":
        show_home_page()
    elif page == "➕ Create Concept":
        show_create_concept_page()
    elif page == "🔍 Search Concepts":
        show_search_page()
    elif page == "📊 Analyze Text":
        show_analyze_page()
    elif page == "🎯 Customer Insights":
        show_insights_page()
    elif page == "📈 Dashboard":
        show_dashboard_page()


def show_home_page():
    """Show home page with introduction and quick demo"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("What is ConceptDB?")
        st.write("""
        ConceptDB is not just another vector database. It's a **Concept-Type Database** 
        that truly understands the meaning and relationships between concepts.
        
        ### Key Features:
        - 🎯 **Semantic Understanding**: Goes beyond keywords to understand meaning
        - 🔗 **Concept Relationships**: Automatically discovers and manages relationships
        - 📊 **Business Insights**: Transforms unstructured data into actionable insights
        - ⚡ **Real-time Analysis**: Instant concept extraction and analysis
        """)
        
        st.info("""
        **Try it out!** 
        1. Create concepts in the "Create Concept" page
        2. Search using natural language in "Search Concepts"
        3. Analyze customer feedback in "Customer Insights"
        """)
    
    with col2:
        st.header("Quick Demo")
        
        # Demo search
        st.subheader("Try Semantic Search")
        demo_query = st.text_input("Enter a search query:", "customer happiness")
        if st.button("Search", key="demo_search"):
            with st.spinner("Searching..."):
                results = search_concepts(demo_query, limit=3)
                if results:
                    st.success(f"Found {len(results)} concepts")
                    for result in results:
                        concept = result.get("concept", {})
                        score = result.get("similarity_score", 0)
                        st.write(f"**{concept.get('name', 'Unknown')}** (Score: {score:.2%})")
                        st.write(f"_{concept.get('description', 'No description')}_")
                else:
                    st.info("No concepts found. Try creating some first!")


def show_create_concept_page():
    """Show concept creation page"""
    st.header("➕ Create New Concept")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Concept Name", placeholder="e.g., customer satisfaction")
        description = st.text_area(
            "Description", 
            placeholder="Describe what this concept means...",
            height=150
        )
        
        # Metadata
        st.subheader("Metadata (Optional)")
        category = st.text_input("Category", placeholder="e.g., business")
        tags = st.text_input("Tags (comma-separated)", placeholder="e.g., customer, metrics, kpi")
        domain = st.text_input("Domain", placeholder="e.g., customer service")
    
    with col2:
        st.subheader("Preview")
        if name and description:
            st.markdown(f"### {name}")
            st.write(description)
            
            if category or tags or domain:
                st.write("**Metadata:**")
                if category:
                    st.write(f"- Category: {category}")
                if tags:
                    st.write(f"- Tags: {tags}")
                if domain:
                    st.write(f"- Domain: {domain}")
        else:
            st.info("Enter a name and description to see preview")
    
    if st.button("Create Concept", type="primary"):
        if name and description:
            with st.spinner("Creating concept..."):
                metadata = {}
                if category:
                    metadata["category"] = category
                if tags:
                    metadata["tags"] = [t.strip() for t in tags.split(",")]
                if domain:
                    metadata["domain"] = domain
                
                result = create_concept(name, description, metadata)
                if result:
                    st.success(f"✅ Concept '{name}' created successfully!")
                    st.json(result)
                else:
                    st.error("Failed to create concept")
        else:
            st.warning("Please enter both name and description")


def show_search_page():
    """Show semantic search page"""
    st.header("🔍 Semantic Search")
    
    st.write("Search for concepts using natural language. ConceptDB understands meaning, not just keywords!")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        query = st.text_input("Search Query", placeholder="e.g., user happiness and satisfaction")
    with col2:
        limit = st.number_input("Max Results", min_value=1, max_value=50, value=10)
    with col3:
        threshold = st.slider("Similarity Threshold", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
    
    if st.button("Search", type="primary"):
        if query:
            with st.spinner("Searching..."):
                results = search_concepts(query, limit, threshold)
                
                if results:
                    st.success(f"Found {len(results)} concepts")
                    
                    # Display results
                    for i, result in enumerate(results, 1):
                        concept = result.get("concept", {})
                        score = result.get("similarity_score", 0)
                        
                        with st.expander(f"{i}. {concept.get('name', 'Unknown')} - Score: {score:.2%}"):
                            st.write(f"**Description:** {concept.get('description', 'No description')}")
                            st.write(f"**ID:** `{concept.get('id', 'N/A')}`")
                            st.write(f"**Strength:** {concept.get('strength', 0):.2f}")
                            st.write(f"**Usage Count:** {concept.get('usage_count', 0)}")
                            
                            metadata = concept.get("metadata", {})
                            if metadata:
                                st.write("**Metadata:**")
                                st.json(metadata)
                            
                            relationships = concept.get("relationships", {})
                            if any(relationships.values()):
                                st.write("**Relationships:**")
                                for rel_type, rel_ids in relationships.items():
                                    if rel_ids:
                                        st.write(f"- {rel_type}: {len(rel_ids)} concepts")
                else:
                    st.info("No concepts found. Try adjusting the threshold or creating more concepts.")
        else:
            st.warning("Please enter a search query")


def show_analyze_page():
    """Show text analysis page"""
    st.header("📊 Text Analysis")
    
    st.write("Analyze text to extract concepts, keywords, and sentiment.")
    
    text = st.text_area(
        "Enter text to analyze",
        placeholder="Paste customer feedback, product reviews, or any text here...",
        height=200
    )
    
    col1, col2 = st.columns(2)
    with col1:
        extract_concepts = st.checkbox("Extract Concepts", value=True)
        auto_create = st.checkbox("Auto-create New Concepts", value=False)
    with col2:
        max_concepts = st.number_input("Max Concepts", min_value=1, max_value=20, value=5)
    
    if st.button("Analyze Text", type="primary"):
        if text:
            with st.spinner("Analyzing..."):
                result = analyze_text(text, extract_concepts, auto_create)
                
                if result:
                    # Display results in columns
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("📝 Keywords")
                        keywords = result.get("keywords", [])
                        if keywords:
                            for keyword in keywords:
                                st.write(f"• {keyword}")
                        else:
                            st.info("No keywords extracted")
                    
                    with col2:
                        st.subheader("🎭 Sentiment")
                        sentiment = result.get("sentiment", {})
                        if sentiment:
                            positive = sentiment.get("positive", 0) * 100
                            negative = sentiment.get("negative", 0) * 100
                            neutral = sentiment.get("neutral", 0) * 100
                            
                            st.metric("Positive", f"{positive:.1f}%")
                            st.metric("Negative", f"{negative:.1f}%")
                            st.metric("Neutral", f"{neutral:.1f}%")
                        else:
                            st.info("No sentiment data")
                    
                    with col3:
                        st.subheader("🧠 Concepts")
                        existing = result.get("existing_concepts", [])
                        new = result.get("new_concepts", [])
                        
                        if existing:
                            st.write("**Existing:**")
                            for concept in existing:
                                st.write(f"• {concept.get('name', 'Unknown')}")
                        
                        if new:
                            st.write("**New (created):**")
                            for concept in new:
                                st.write(f"• {concept.get('name', 'Unknown')}")
                        
                        if not existing and not new:
                            st.info("No concepts found")
                else:
                    st.error("Analysis failed")
        else:
            st.warning("Please enter some text to analyze")


def show_insights_page():
    """Show customer insights demo page"""
    st.header("🎯 Customer Insights Demo")
    
    st.write("Analyze customer feedback to extract business insights automatically.")
    
    # Sample feedbacks
    sample_feedbacks = [
        "The product quality is excellent, but the shipping was slower than expected.",
        "Great customer service! They resolved my issue quickly and professionally.",
        "The price is a bit high, but the quality justifies it.",
        "Easy to use interface, but lacks some advanced features.",
        "Fast delivery and well-packaged. Very satisfied with my purchase.",
        "The product didn't meet my expectations. Poor build quality.",
        "Amazing experience! Will definitely recommend to friends.",
        "Good value for money, but the documentation could be better.",
        "The return process was hassle-free. Appreciate the customer-first approach.",
        "Product works as advertised. No complaints so far."
    ]
    
    st.subheader("Customer Feedback")
    
    # Text area for feedbacks
    feedbacks_text = st.text_area(
        "Enter customer feedbacks (one per line)",
        value="\n".join(sample_feedbacks),
        height=300
    )
    
    if st.button("Analyze Feedbacks", type="primary"):
        feedbacks = [f.strip() for f in feedbacks_text.split("\n") if f.strip()]
        
        if feedbacks:
            with st.spinner("Analyzing customer feedback..."):
                # Analyze each feedback
                all_concepts = []
                all_keywords = []
                sentiment_scores = {"positive": 0, "negative": 0, "neutral": 0}
                
                for feedback in feedbacks:
                    result = analyze_text(feedback, extract_concepts=True, auto_create=False)
                    if result:
                        all_concepts.extend(result.get("extracted_concepts", []))
                        all_keywords.extend(result.get("keywords", []))
                        
                        sentiment = result.get("sentiment", {})
                        sentiment_scores["positive"] += sentiment.get("positive", 0)
                        sentiment_scores["negative"] += sentiment.get("negative", 0)
                        sentiment_scores["neutral"] += sentiment.get("neutral", 0)
                
                # Aggregate results
                total_feedbacks = len(feedbacks)
                
                # Normalize sentiment
                for key in sentiment_scores:
                    sentiment_scores[key] = (sentiment_scores[key] / total_feedbacks) * 100
                
                # Count concept frequency
                from collections import Counter
                concept_counts = Counter(all_concepts)
                keyword_counts = Counter(all_keywords)
                
                # Display insights
                st.success(f"Analyzed {total_feedbacks} customer feedbacks")
                
                # Metrics row
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Feedbacks", total_feedbacks)
                with col2:
                    st.metric("Positive Sentiment", f"{sentiment_scores['positive']:.1f}%")
                with col3:
                    st.metric("Negative Sentiment", f"{sentiment_scores['negative']:.1f}%")
                with col4:
                    st.metric("Unique Concepts", len(set(all_concepts)))
                
                # Visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Concept Heatmap")
                    if concept_counts:
                        df = pd.DataFrame(
                            concept_counts.most_common(10),
                            columns=["Concept", "Frequency"]
                        )
                        fig = px.bar(df, x="Frequency", y="Concept", orientation='h',
                                    title="Top 10 Concepts Mentioned")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No concepts extracted")
                
                with col2:
                    st.subheader("🔑 Key Themes")
                    if keyword_counts:
                        top_keywords = keyword_counts.most_common(10)
                        for keyword, count in top_keywords:
                            st.write(f"• **{keyword}** ({count} mentions)")
                    else:
                        st.info("No keywords extracted")
                
                # Recommendations
                st.subheader("💡 AI-Generated Insights")
                
                insights = []
                if sentiment_scores["positive"] > 60:
                    insights.append("✅ Overall customer sentiment is positive")
                elif sentiment_scores["negative"] > 40:
                    insights.append("⚠️ Significant negative sentiment detected - immediate attention needed")
                else:
                    insights.append("📊 Mixed customer sentiment - investigate specific issues")
                
                if "shipping" in all_keywords or "delivery" in all_keywords:
                    insights.append("🚚 Shipping/delivery is a key concern for customers")
                
                if "quality" in all_keywords:
                    insights.append("🏆 Product quality is frequently mentioned")
                
                if "price" in all_keywords or "cost" in all_keywords:
                    insights.append("💰 Pricing is a significant factor in customer feedback")
                
                if "service" in all_keywords or "support" in all_keywords:
                    insights.append("🤝 Customer service is an important touchpoint")
                
                for insight in insights:
                    st.write(insight)
        else:
            st.warning("Please enter some customer feedback")


def show_dashboard_page():
    """Show dashboard with overall statistics"""
    st.header("📈 ConceptDB Dashboard")
    
    # Get all concepts for statistics
    concepts = get_all_concepts(page=1, page_size=100)
    
    if concepts:
        # Calculate statistics
        total_concepts = len(concepts)
        total_usage = sum(c.get("usage_count", 0) for c in concepts)
        avg_strength = sum(c.get("strength", 0) for c in concepts) / total_concepts if total_concepts > 0 else 0
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Concepts", total_concepts)
        with col2:
            st.metric("Total Usage", total_usage)
        with col3:
            st.metric("Avg Strength", f"{avg_strength:.2f}")
        with col4:
            st.metric("API Status", "🟢 Online")
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Top Concepts by Usage")
            top_concepts = sorted(concepts, key=lambda x: x.get("usage_count", 0), reverse=True)[:10]
            if top_concepts:
                df = pd.DataFrame([
                    {"Name": c.get("name", "Unknown"), "Usage": c.get("usage_count", 0)}
                    for c in top_concepts
                ])
                fig = px.bar(df, x="Name", y="Usage", title="Most Used Concepts")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("💪 Concept Strength Distribution")
            strengths = [c.get("strength", 0) for c in concepts]
            fig = go.Figure(data=[go.Histogram(x=strengths, nbinsx=20)])
            fig.update_layout(title="Distribution of Concept Strengths",
                            xaxis_title="Strength", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent concepts table
        st.subheader("📝 Recent Concepts")
        recent_concepts = sorted(concepts, 
                                key=lambda x: x.get("created_at", ""), 
                                reverse=True)[:10]
        
        if recent_concepts:
            table_data = []
            for c in recent_concepts:
                table_data.append({
                    "Name": c.get("name", "Unknown"),
                    "Description": c.get("description", "")[:50] + "...",
                    "Strength": c.get("strength", 0),
                    "Usage": c.get("usage_count", 0),
                    "Created": c.get("created_at", "Unknown")[:19]
                })
            
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No concepts found. Start by creating some concepts!")


if __name__ == "__main__":
    main()