#!/usr/bin/env python3
"""
Flight Schedule Parser and Query Tool
Python Final Assignment
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

class FlightValidator:
    ORIGIN_CODES = {'LHR', 'JFK', 'FRA', 'RIX', 'OSL', 'HEL', 'CDG', 'DXB', 'AMS', 'ARN', 'DOH', 'SYD', 'LAX', 'BRU'}
    
    @staticmethod
    def validate_flightid(flight_id):
        if not flight_id or len(flight_id) > 8:
            return False, "flightid too long (more than 8 characters)" if flight_id and len(flight_id) > 8 else "missing flightid field"
        if not flight_id.isalnum():
            return False, "invalid flightid format"
        return True, ""
    
    @staticmethod
    def validate_code(code):
        if not code or len(code) != 3 or not code.isupper() or not code.isalpha():
            return False, ""
        return True, ""
    
    @staticmethod
    def validate_datetime(dt_str):
        try:
            if not dt_str:
                return False, ""
            datetime.strptime(dt_str, '%Y-%m-%d %H%M')
            return True, ""
        except ValueError:
            return False, ""
    
    @staticmethod
    def validate_price(price_str):
        try:
            if not price_str:
                return False, "missing price field"
            price = float(price_str)
            if price < 0:
                return False, "negative price value"
            return True, ""
        except ValueError:
            return False, "invalid price format"
    
    @staticmethod
    def validate_flight_record(record, line_num):
        errors = []
        
        fields = ['flightid', 'origin', 'destination', 'departuredatetime', 'arrivaldatetime', 'price']
        for field in fields:
            val = record.get(field)
            if not val:
                errors.append(f"missing {field} field")
                return False, ", ".join(errors)
        
        valid, msg = FlightValidator.validate_flightid(record['flightid'])
        if not valid:
            errors.append(msg)
        
        valid, _ = FlightValidator.validate_code(record['origin'])
        if not valid:
            errors.append("invalid origin code")
        elif record['origin'] not in FlightValidator.ORIGIN_CODES:
            errors.append("invalid origin code")
        
        valid, _ = FlightValidator.validate_code(record['destination'])
        if not valid:
            errors.append("invalid destination code")
        
        depart_valid, _ = FlightValidator.validate_datetime(record['departuredatetime'])
        if not depart_valid:
            errors.append("invalid departure datetime")
        
        arrive_valid, _ = FlightValidator.validate_datetime(record['arrivaldatetime'])
        if not arrive_valid:
            errors.append("invalid arrival datetime")
        
        if depart_valid and arrive_valid:
            depart_dt = datetime.strptime(record['departuredatetime'], '%Y-%m-%d %H%M')
            arrive_dt = datetime.strptime(record['arrivaldatetime'], '%Y-%m-%d %H%M')
            if arrive_dt <= depart_dt:
                errors.append("arrival before departure")
        
        valid, msg = FlightValidator.validate_price(record['price'])
        if not valid:
            errors.append(msg)
        
        return len(errors) == 0, ", ".join(errors) if errors else ""

class FlightParser:
    def __init__(self):
        self.valid_flights = []
        self.error_lines = []
    
    def parse_csv(self, filepath):
        line_num = 0
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, fieldnames=['flightid', 'origin', 'destination', 'departuredatetime', 'arrivaldatetime', 'price'])
                for row in reader:
                    line_num += 1
                    if row['flightid'] == 'flightid' or not any(row.values()):
                        continue
                    
                    if 'Valid flights' in str(row.get('flightid', '')) or 'Invalid flights' in str(row.get('flightid', '')):
                        self.error_lines.append((line_num, f"Line {line_num} {row.get('flightid', '')} comment line, ignored for data parsing"))
                        continue
                    
                    valid, errors = FlightValidator.validate_flight_record(row, line_num)
                    if valid:
                        self.valid_flights.append(row)
                    else:
                        self.error_lines.append((line_num, errors))
        except Exception as e:
            print(f"Error reading file {filepath}: {e}", file=sys.stderr)
    
    def parse_directory(self, dirpath):
        path = Path(dirpath)
        for csv_file in sorted(path.glob('*.csv')):
            self.parse_csv(str(csv_file))
    
    def export_valid_flights(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.valid_flights, f, indent=2)
    
    def export_errors(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            for line_num, error in self.error_lines:
                f.write(f"Line {line_num} {error}\n")
    
    def load_json_database(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.valid_flights = json.load(f)
        except Exception as e:
            print(f"Error loading JSON file {filepath}: {e}", file=sys.stderr)
            sys.exit(1)
    
    def query_flights(self, query):
        results = []
        for flight in self.valid_flights:
            match = True
            if 'flightid' in query and flight['flightid'] != query['flightid']:
                match = False
            if 'origin' in query and flight['origin'] != query['origin']:
                match = False
            if 'destination' in query and flight['destination'] != query['destination']:
                match = False
            if 'departuredatetime' in query and query['departuredatetime'] not in flight['departuredatetime']:
                match = False
            if 'arrivaldatetime' in query and query['arrivaldatetime'] not in flight['arrivaldatetime']:
                match = False
            if 'price' in query:
                try:
                    query_price = float(query['price'])
                    flight_price = float(flight['price'])
                    if flight_price != query_price:
                        match = False
                except ValueError:
                    match = False
            if match:
                results.append(flight)
        return results
    
    def execute_queries(self, query_path):
        try:
            with open(query_path, 'r', encoding='utf-8') as f:
                queries_data = json.load(f)
            if isinstance(queries_data, dict):
                queries = [queries_data]
            else:
                queries = queries_data
            results = []
            for query in queries:
                matches = self.query_flights(query)
                results.append({'query': query, 'matches': matches})
            return results
        except Exception as e:
            print(f"Error executing queries from {query_path}: {e}", file=sys.stderr)
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Flight Schedule Parser and Query Tool', prog='flightparser.py')
    parser.add_argument('-i', '--input', help='Parse a single CSV file')
    parser.add_argument('-d', '--directory', help='Parse all CSV files in a directory')
    parser.add_argument('-o', '--output', help='Output path for valid flights JSON', default='db.json')
    parser.add_argument('-j', '--json', help='Load existing JSON database')
    parser.add_argument('-q', '--query', help='Query file in JSON format')
    
    args = parser.parse_args()
    flight_parser = FlightParser()
    
    if args.input:
        flight_parser.parse_csv(args.input)
        flight_parser.export_valid_flights(args.output)
        flight_parser.export_errors('errors.txt')
    elif args.directory:
        flight_parser.parse_directory(args.directory)
        flight_parser.export_valid_flights(args.output)
        flight_parser.export_errors('errors.txt')
    elif args.json:
        flight_parser.load_json_database(args.json)
    else:
        parser.print_help()
        sys.exit(1)
    
    if args.query:
        results = flight_parser.execute_queries(args.query)
        response_filename = 'response.json'
        with open(response_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"Query results saved to {response_filename}")
    
    print("Processing complete.")

if __name__ == '__main__':
    main()
