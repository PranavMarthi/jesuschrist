#!/usr/bin/env python3
"""Extract questions and build question-to-URL mapping from allqslinks.txt."""

import json
import sys
from pathlib import Path


def parse_allqslinks(input_path: str) -> tuple[list[str], dict[str, str]]:
    """Parse allqslinks.txt into questions list and question->URL mapping.
    
    Format: "Question, URL" per line
    
    Returns:
        (questions_list, question_url_map)
    """
    path = Path(input_path)
    if not path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)
    
    questions = []
    url_map = {}
    
    with path.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            
            # Split by finding the URL pattern (https://)
            # Handle both "question?, https://..." and "question, https://..." formats
            url_start = line.find(', https://')
            
            if url_start == -1:
                # Try without question mark
                url_start = line.find(' https://')
                if url_start == -1:
                    print(f"Warning: Line {line_num} malformed (no URL found), skipping: {line[:60]}", file=sys.stderr)
                    continue
                question = line[:url_start].strip()
                url = line[url_start + 1:].strip()
            else:
                question = line[:url_start].strip()
                url = line[url_start + 2:].strip()  # Skip ", "
            
            if not question or not url:
                print(f"Warning: Line {line_num} has empty question or URL, skipping", file=sys.stderr)
                continue
            
            questions.append(question)
            url_map[question] = url
    
    return questions, url_map


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_questions.py <allqslinks.txt>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    print(f"Parsing {input_file}...", file=sys.stderr)
    questions, url_map = parse_allqslinks(input_file)
    
    print(f"Extracted {len(questions)} questions", file=sys.stderr)
    print(f"Built URL map with {len(url_map)} entries", file=sys.stderr)
    
    # Write questions_only.txt
    questions_file = Path(input_file).parent / "questions_only.txt"
    with questions_file.open('w', encoding='utf-8') as f:
        for q in questions:
            f.write(q + '\n')
    print(f"Wrote {questions_file}", file=sys.stderr)
    
    # Write question_url_map.json
    map_file = Path(input_file).parent / "question_url_map.json"
    with map_file.open('w', encoding='utf-8') as f:
        json.dump(url_map, f, ensure_ascii=False, indent=2)
    print(f"Wrote {map_file}", file=sys.stderr)
    
    print("Done!", file=sys.stderr)


if __name__ == "__main__":
    main()
