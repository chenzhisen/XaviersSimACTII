#!/usr/bin/env python3

import os
import sys
import json
import base64
import fnmatch
import argparse
import requests

def cleanup_files(patterns="*", is_production=False):
    """Clean up files matching any of the patterns in the appropriate directory."""
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        return
        
    pattern_list = [p.strip() for p in patterns.split('|')]
    base_dir = "prod" if is_production else "dev"
    data_dir = f"data/{base_dir}"
    
    print(f"\nStarting cleanup process:")
    print(f"Base directory: {data_dir}")
    print(f"Patterns to match: {pattern_list}")
    
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    base_url = "https://api.github.com"
    repo_owner = "0xDatapunk"
    repo_name = "XaviersSimACTII"
    
    try:
        def get_contents(path):
            url = f"{base_url}/repos/{repo_owner}/{repo_name}/contents/{path}"
            print(f"\nFetching contents of: {path}")
            print(f"API URL: {url}")
            
            response = requests.get(url, headers=headers)
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 404:
                print(f"Path not found: {path}")
                return []
                
            response.raise_for_status()
            content = response.json()
            
            if isinstance(content, list):
                print(f"Found {len(content)} items in directory")
                for item in content:
                    print(f"- {item['type']}: {item['path']}")
            else:
                print(f"Found single item: {content['type']} - {content['path']}")
            
            return content
            
        def delete_file(path, sha):
            """Delete a specific file"""
            print(f"\nDeleting: {path}")
            print(f"SHA: {sha}")
            
            try:
                delete_url = f"{base_url}/repos/{repo_owner}/{repo_name}/contents/{path}"
                delete_data = {
                    'message': f"Cleanup: Remove {os.path.basename(path)}",
                    'sha': sha
                }
                
                print(f"Delete URL: {delete_url}")
                print(f"Delete data: {json.dumps(delete_data, indent=2)}")
                
                response = requests.delete(delete_url, headers=headers, json=delete_data)
                print(f"Delete response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"Response content: {response.text}")
                    
                response.raise_for_status()
                print(f"Successfully deleted: {path}")
                return True
            except Exception as e:
                print(f"Error deleting {path}: {str(e)}")
                return False
            
        def delete_contents(path):
            """Recursively delete contents"""
            contents = get_contents(path)
            if not contents:
                return
                
            if not isinstance(contents, list):
                contents = [contents]
                
            # First handle all files
            for content in contents:
                if content['type'] == "file":
                    file_path = content['path']
                    full_path = file_path.replace(data_dir + '/', '')  # Remove base dir prefix
                    
                    print(f"\nChecking file: {file_path}")
                    print(f"Normalized path: {full_path}")
                    print(f"Against patterns: {pattern_list}")
                    
                    # Check if file matches any pattern
                    for pattern in pattern_list:
                        # Try different path formats
                        if (fnmatch.fnmatch(full_path, pattern) or 
                            fnmatch.fnmatch(file_path, pattern) or 
                            fnmatch.fnmatch(os.path.basename(file_path), pattern)):
                            print(f"Pattern '{pattern}' matched!")
                            delete_file(file_path, content['sha'])
                            break
                        else:
                            print(f"Pattern '{pattern}' did not match")
            
            # Then handle directories
            for content in contents:
                if content['type'] == "dir":
                    dir_path = content['path']
                    dir_name = os.path.basename(dir_path)
                    
                    print(f"\nProcessing directory: {dir_path}")
                    
                    # Recursively process directory contents
                    delete_contents(dir_path)
                    
                    # Check if empty directory should be deleted
                    if any(fnmatch.fnmatch(dir_name, pattern) for pattern in pattern_list):
                        print(f"Directory '{dir_name}' matches pattern")
                        remaining = get_contents(dir_path)
                        if not remaining:
                            print("Directory is empty, deleting...")
                            delete_file(dir_path, content['sha'])
                        else:
                            print("Directory not empty, skipping deletion")
        
        delete_contents(data_dir)
        print("\nCleanup process complete")
        
    except Exception as e:
        print(f"\nError during cleanup: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up files from GitHub repository")
    parser.add_argument("patterns", help="File patterns to match, separated by |")
    parser.add_argument("--production", action="store_true", help="Clean production files")
    args = parser.parse_args()
    
    cleanup_files(patterns=args.patterns, is_production=args.production) 