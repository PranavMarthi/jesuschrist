#!/usr/bin/env python3
"""Merge Polymarket URLs into geocoded results and cache."""

import json
import re
import sys
from pathlib import Path


def normalize_question(question: str) -> str:
    """Normalize question text for better matching."""
    # Lowercase
    normalized = question.lower().strip()
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    # Remove punctuation except question marks
    normalized = re.sub(r'[^\w\s?-]', '', normalized)
    return normalized


def merge_links_into_results(results_path: str, url_map_path: str, output_path: str):
    """Merge URL links into geocoded results JSON."""
    
    # Load geocoded results
    print(f"Loading geocoded results from {results_path}...", file=sys.stderr)
    with open(results_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Load URL map
    print(f"Loading URL map from {url_map_path}...", file=sys.stderr)
    with open(url_map_path, 'r', encoding='utf-8') as f:
        url_map = json.load(f)
    
    # Build normalized lookup
    print("Building normalized question lookup...", file=sys.stderr)
    normalized_url_map = {}
    for question, url in url_map.items():
        norm_q = normalize_question(question)
        normalized_url_map[norm_q] = url
    
    # Merge
    print(f"Merging links into {len(results)} results...", file=sys.stderr)
    exact_matches = 0
    normalized_matches = 0
    no_matches = 0
    
    for item in results:
        question = item.get('question', '')
        
        # Try exact match first
        if question in url_map:
            item['link'] = url_map[question]
            exact_matches += 1
        else:
            # Try normalized match
            norm_q = normalize_question(question)
            if norm_q in normalized_url_map:
                item['link'] = normalized_url_map[norm_q]
                normalized_matches += 1
            else:
                item['link'] = None
                no_matches += 1
    
    # Save
    print(f"Writing merged results to {output_path}...", file=sys.stderr)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nMerge complete!", file=sys.stderr)
    print(f"  Exact matches: {exact_matches}", file=sys.stderr)
    print(f"  Normalized matches: {normalized_matches}", file=sys.stderr)
    print(f"  No matches: {no_matches}", file=sys.stderr)
    print(f"  Total: {len(results)}", file=sys.stderr)


def merge_links_into_cache(cache_path: str, url_map_path: str):
    """Merge URL links into geocode cache."""
    
    # Load cache
    print(f"Loading cache from {cache_path}...", file=sys.stderr)
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    # Load URL map
    print(f"Loading URL map from {url_map_path}...", file=sys.stderr)
    with open(url_map_path, 'r', encoding='utf-8') as f:
        url_map = json.load(f)
    
    # Build normalized lookup
    print("Building normalized question lookup...", file=sys.stderr)
    normalized_url_map = {}
    for question, url in url_map.items():
        norm_q = normalize_question(question)
        normalized_url_map[norm_q] = url
    
    # Merge
    print(f"Merging links into {len(cache)} cache entries...", file=sys.stderr)
    exact_matches = 0
    normalized_matches = 0
    no_matches = 0
    
    for question, data in cache.items():
        # Try exact match first
        if question in url_map:
            data['link'] = url_map[question]
            exact_matches += 1
        else:
            # Try normalized match
            norm_q = normalize_question(question)
            if norm_q in normalized_url_map:
                data['link'] = normalized_url_map[norm_q]
                normalized_matches += 1
            else:
                data['link'] = None
                no_matches += 1
    
    # Save
    print(f"Writing merged cache to {cache_path}...", file=sys.stderr)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    print(f"\nCache merge complete!", file=sys.stderr)
    print(f"  Exact matches: {exact_matches}", file=sys.stderr)
    print(f"  Normalized matches: {normalized_matches}", file=sys.stderr)
    print(f"  No matches: {no_matches}", file=sys.stderr)
    print(f"  Total: {len(cache)}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: python merge_links.py <command>")
        print("Commands:")
        print("  results - Merge links into polymarket_all_results.json")
        print("  cache   - Merge links into .geolocate_cache.json")
        print("  both    - Merge links into both files")
        sys.exit(1)
    
    command = sys.argv[1]
    base_dir = Path(__file__).parent
    
    url_map_path = base_dir / "question_url_map.json"
    results_path = base_dir / "polymarket_all_results.json"
    cache_path = base_dir / ".geolocate_cache.json"
    
    if command == "results":
        output_path = base_dir / "polymarket_all_results_with_links.json"
        merge_links_into_results(str(results_path), str(url_map_path), str(output_path))
    
    elif command == "cache":
        merge_links_into_cache(str(cache_path), str(url_map_path))
    
    elif command == "both":
        output_path = base_dir / "polymarket_all_results_with_links.json"
        merge_links_into_results(str(results_path), str(url_map_path), str(output_path))
        merge_links_into_cache(str(cache_path), str(url_map_path))
    
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
