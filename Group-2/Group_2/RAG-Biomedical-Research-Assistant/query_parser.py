import re
from datetime import datetime

class QueryParser:

    def parse_structured_query(self, query: str):
        patterns = {
            'research_keyword': r'What is the\s+(.+?)\s+of',
            'intervention': r'of\s+(.+?)\s+in',
            'condition': r'in\s+(.+?)\s+from papers',
            'timeframe': r'published in\s+(.+?)\??$'
        }

        parsed = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            parsed[key] = match.group(1).strip() if match else ""

        return parsed

    def parse_timeframe(self, timeframe_str: str):
        if '-' in timeframe_str:
            numbers = re.findall(r'\d{4}', timeframe_str)
            if len(numbers) == 2:
                return int(numbers[0]), int(numbers[1])

        match = re.search(r'\d{4}', timeframe_str)
        if match:
            return int(match.group()), int(match.group())

        current_year = datetime.now().year
        return current_year-5, current_year