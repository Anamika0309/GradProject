"""
Phase 2 – Rule-Based Review Analyzer (Free Alternative)
========================================================
Analyzes Spotify reviews using keyword matching and sentiment analysis
without requiring paid APIs. Uses VADER for sentiment analysis.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import Counter
from datetime import datetime, timezone
import sys

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    print("Installing vaderSentiment...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "vaderSentiment"])
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class RuleBasedAnalyzer:
    """Free rule-based analysis system for Spotify reviews"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Keyword dictionaries for pain points
        self.discovery_keywords = [
            "discover weekly", "discover", "recommendation", "recommend", 
            "algorithm", "new music", "find music", "suggestion", "radio"
        ]
        
        self.search_keywords = [
            "search", "find song", "can't find", "search bar", "lookup",
            "searching", "search function", "search results"
        ]
        
        self.playlist_keywords = [
            "playlist", "queue", "shuffle", "library", "saved songs",
            "my playlist", "create playlist", "add to playlist"
        ]
        
        self.crash_keywords = [
            "crash", "freeze", "bug", "glitch", "slow", "lag", "stuck",
            "not working", "broken", "error", "loading", "buffer"
        ]
        
        # User segment keywords
        self.student_keywords = ["student", "college", "university", "study", "studying", "homework"]
        self.gym_keywords = ["gym", "workout", "exercise", "running", "fitness", "training"]
        self.parent_keywords = ["parent", "kids", "children", "family", "son", "daughter", "baby"]
        self.casual_keywords = ["casual", "background", "chill", "relax", "occasional"]
        self.audiophile_keywords = ["audiophile", "quality", "sound", "audio", "bitrate", "hi-fi", "lossless"]
        
        # Feature request keywords
        self.feature_keywords = [
            "feature", "add", "should have", "need", "want", "wish",
            "missing", "please add", "would be nice", "option", "setting"
        ]
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using VADER"""
        scores = self.sentiment_analyzer.polarity_scores(text)
        
        if scores['compound'] >= 0.05:
            overall = "Happy"
        elif scores['compound'] <= -0.05:
            overall = "Angry"
        else:
            overall = "Neutral"
        
        return {
            "overall": overall,
            "confidence": abs(scores['compound']),
            "key_emotions": [],
            "summary": f"Sentiment score: {scores['compound']:.2f} (positive: {scores['pos']:.2f}, negative: {scores['neg']:.2f})"
        }
    
    def extract_pain_points(self, text: str) -> Dict[str, List[str]]:
        """Extract pain points using keyword matching"""
        text_lower = text.lower()
        
        pain_points = {
            "discovery_issues": [],
            "recommendation_issues": [],
            "search_issues": [],
            "playlist_issues": [],
            "other_issues": []
        }
        
        # Check each category
        for keyword in self.discovery_keywords:
            if keyword in text_lower:
                pain_points["discovery_issues"].append(f"Mentioned: {keyword}")
        
        for keyword in self.search_keywords:
            if keyword in text_lower:
                pain_points["search_issues"].append(f"Mentioned: {keyword}")
        
        for keyword in self.playlist_keywords:
            if keyword in text_lower:
                pain_points["playlist_issues"].append(f"Mentioned: {keyword}")
        
        for keyword in self.crash_keywords:
            if keyword in text_lower:
                pain_points["other_issues"].append(f"Technical issue: {keyword}")
        
        return pain_points
    
    def detect_user_segment(self, text: str) -> Dict[str, Any]:
        """Detect user segment using keyword matching"""
        text_lower = text.lower()
        
        segments = {
            "Student": sum(1 for kw in self.student_keywords if kw in text_lower),
            "Gym User": sum(1 for kw in self.gym_keywords if kw in text_lower),
            "Parent": sum(1 for kw in self.parent_keywords if kw in text_lower),
            "Casual": sum(1 for kw in self.casual_keywords if kw in text_lower),
            "Audiophile": sum(1 for kw in self.audiophile_keywords if kw in text_lower)
        }
        
        # Get segment with highest match count
        if any(segments.values()):
            primary_segment = max(segments, key=segments.get)
            confidence = segments[primary_segment] / max(len(self.student_keywords), 1)
        else:
            primary_segment = "Unknown"
            confidence = 0.0
        
        # Find evidence
        evidence = []
        if primary_segment == "Student":
            evidence = [kw for kw in self.student_keywords if kw in text_lower]
        elif primary_segment == "Gym User":
            evidence = [kw for kw in self.gym_keywords if kw in text_lower]
        elif primary_segment == "Parent":
            evidence = [kw for kw in self.parent_keywords if kw in text_lower]
        elif primary_segment == "Casual":
            evidence = [kw for kw in self.casual_keywords if kw in text_lower]
        elif primary_segment == "Audiophile":
            evidence = [kw for kw in self.audiophile_keywords if kw in text_lower]
        
        return {
            "primary_segment": primary_segment,
            "confidence": min(confidence, 1.0),
            "evidence": evidence[:3],
            "secondary_segments": []
        }
    
    def extract_feature_requests(self, text: str) -> Dict[str, List[str]]:
        """Extract feature requests using keyword matching"""
        text_lower = text.lower()
        
        if not any(kw in text_lower for kw in self.feature_keywords):
            return {"critical_needs": [], "nice_to_wants": [], "missing_features": [], "improvements": []}
        
        # Extract sentences containing feature keywords
        sentences = re.split(r'[.!?]+', text)
        feature_sentences = [s.strip() for s in sentences if any(kw in s.lower() for kw in self.feature_keywords)]
        
        return {
            "critical_needs": feature_sentences[:2],
            "nice_to_wants": [],
            "missing_features": feature_sentences[:2],
            "improvements": feature_sentences[:2]
        }
    
    def generate_insights(self, review_text: str, sentiment: Dict, pain_points: Dict, 
                          user_segment: Dict, feature_requests: Dict) -> Dict[str, List[str]]:
        """Synthesize all analysis into final insights"""
        all_issues = []
        all_issues.extend(pain_points["discovery_issues"])
        all_issues.extend(pain_points["search_issues"])
        all_issues.extend(pain_points["playlist_issues"])
        all_issues.extend(pain_points["other_issues"])
        
        top_complaints = all_issues[:5] if all_issues else ["No specific complaints identified"]
        
        user_segments = [user_segment["primary_segment"]] if user_segment["primary_segment"] != "Unknown" else ["General user"]
        
        feature_requests_list = feature_requests["critical_needs"] + feature_requests["missing_features"]
        
        unmet_needs = []
        if pain_points["discovery_issues"]:
            unmet_needs.append("Better music discovery")
        if pain_points["search_issues"]:
            unmet_needs.append("Improved search functionality")
        if pain_points["playlist_issues"]:
            unmet_needs.append("Better playlist management")
        
        recommended_opportunities = []
        if sentiment["overall"] == "Angry":
            recommended_opportunities.append("Address user frustration with app stability")
        if pain_points["discovery_issues"]:
            recommended_opportunities.append("Improve recommendation algorithm")
        if feature_requests_list:
            recommended_opportunities.append("Consider implementing requested features")
        
        return {
            "pain_points": list(set(all_issues))[:5],
            "top_complaints": top_complaints[:5],
            "user_segments": user_segments,
            "feature_requests": feature_requests_list[:5],
            "unmet_needs": unmet_needs[:3],
            "recommended_opportunities": recommended_opportunities[:3]
        }
    
    def analyze_review(self, review_text: str) -> Dict[str, Any]:
        """Run complete analysis on a single review"""
        sentiment = self.analyze_sentiment(review_text)
        pain_points = self.extract_pain_points(review_text)
        user_segment = self.detect_user_segment(review_text)
        feature_requests = self.extract_feature_requests(review_text)
        insights = self.generate_insights(review_text, sentiment, pain_points, user_segment, feature_requests)
        
        return {
            "status": "success",
            "sentiment": sentiment,
            "pain_points": insights["pain_points"],
            "top_complaints": insights["top_complaints"],
            "user_segments": insights["user_segments"],
            "feature_requests": insights["feature_requests"],
            "unmet_needs": insights["unmet_needs"],
            "recommended_opportunities": insights["recommended_opportunities"],
            "meta": {
                "model": "rule-based-vader",
                "agents_used": 5
            }
        }
    
    def analyze_batch(self, reviews: List[str]) -> List[Dict[str, Any]]:
        """Analyze multiple reviews"""
        results = []
        for i, review in enumerate(reviews):
            if i % 100 == 0:
                print(f"Analyzing review {i+1}/{len(reviews)}...")
            result = self.analyze_review(review)
            results.append(result)
        return results
    
    def analyze_dataset(self, dataset_path: Path) -> Dict[str, Any]:
        """Analyze entire dataset and generate aggregate insights"""
        print(f"Loading dataset from {dataset_path}...")
        with open(dataset_path, 'r', encoding='utf-8') as f:
            reviews = json.load(f)
        
        print(f"Analyzing {len(reviews)} reviews...")
        results = []
        
        sentiment_counter = Counter()
        segment_counter = Counter()
        all_pain_points = []
        all_feature_requests = []
        
        for i, review in enumerate(reviews):
            if i % 100 == 0:
                print(f"Progress: {i+1}/{len(reviews)} reviews analyzed...")
            
            text = review.get("text", "")
            if not text or len(text.split()) < 5:
                continue
            
            result = self.analyze_review(text)
            results.append(result)
            
            # Aggregate statistics
            sentiment_counter[result["sentiment"]["overall"]] += 1
            segment_counter[result["user_segments"][0] if result["user_segments"] else "Unknown"] += 1
            all_pain_points.extend(result["pain_points"])
            all_feature_requests.extend(result["feature_requests"])
        
        # Generate aggregate insights
        top_pain_points = Counter(all_pain_points).most_common(10)
        top_features = Counter(all_feature_requests).most_common(10)
        
        aggregate_report = {
            "total_reviews_analyzed": len(results),
            "sentiment_distribution": dict(sentiment_counter),
            "user_segment_distribution": dict(segment_counter),
            "top_pain_points": [{"issue": item[0], "count": item[1]} for item in top_pain_points],
            "top_feature_requests": [{"request": item[0], "count": item[1]} for item in top_features],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return aggregate_report


def main():
    """Test the analyzer with sample review"""
    analyzer = RuleBasedAnalyzer()
    
    # Sample review for testing
    sample_review = """
    I've been using Spotify for 3 years and the Discover Weekly has gotten so repetitive. 
    It keeps recommending the same 10 artists every single week. I'm a college student 
    trying to find new music for studying but the algorithm seems broken. The search 
    function is also terrible - it never shows me the songs I actually want. Please fix 
    the recommendation engine!
    """
    
    print("Running rule-based analysis pipeline...")
    result = analyzer.analyze_review(sample_review)
    print("\nAnalysis Result:")
    print(json.dumps(result, indent=2))
    
    # Analyze the full dataset
    dataset_path = Path(__file__).parent.parent / "phase-6" / "storage" / "processed" / "all_reviews.json"
    if dataset_path.exists():
        print(f"\n\nAnalyzing full dataset from {dataset_path}...")
        aggregate = analyzer.analyze_dataset(dataset_path)
        print("\nAggregate Analysis:")
        print(json.dumps(aggregate, indent=2))
        
        # Save aggregate results
        output_path = Path(__file__).parent / "aggregate_analysis.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(aggregate, f, indent=2)
        print(f"\nAggregate analysis saved to {output_path}")
    else:
        print(f"\nDataset not found at {dataset_path}")


if __name__ == "__main__":
    main()
