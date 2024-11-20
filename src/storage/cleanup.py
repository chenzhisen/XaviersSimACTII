from github_operations import GithubOperations
import requests
import sys

def cleanup_path(github_ops, prefix):
    """
    Recursively cleanup files and folders that start with the given prefix
    """
    # List contents in the data directory
    url = f"{github_ops.base_url}/repos/{github_ops.repo_owner}/{github_ops.repo_name}/contents/data"
    response = requests.get(url, headers=github_ops.headers)
    response.raise_for_status()
    
    # Get all items and print them for debugging
    all_items = response.json()
    print("\nAll items in directory:")
    for item in all_items:
        print(f"- {item['name']} (type: {item['type']})")
    
    # Remove 'data/' from prefix if it exists
    clean_prefix = prefix.replace('data/', '')
    print(f"\nLooking for items starting with: '{clean_prefix}'")
    
    # Filter for items that start with the prefix
    items_to_delete = [f for f in all_items if f['name'].startswith(clean_prefix)]
    print(f"Found {len(items_to_delete)} items starting with '{clean_prefix}' in root")
    
    # Delete each item
    for item in items_to_delete:
        try:
            if item['type'] == 'dir':
                print(f"Removing directory: {item['name']}")
                # For directories, we need to recursively delete contents first
                cleanup_path(github_ops, f"{item['name']}")
            
            print(f"Removing: {item['name']}")
            github_ops.delete_file(
                file_path=item['name'],
                commit_message=f"Remove {item['type']}: {item['name']}",
                sha=item['sha']
            )
            print(f"Removed: {item['name']}")
        except Exception as e:
            print(f"Error removing {item['name']}: {e}")

def cleanup_files(prefix):
    """
    Cleanup files and folders that start with the given prefix
    """
    github_ops = GithubOperations()
    cleanup_path(github_ops, prefix)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cleanup.py <file_pattern>")
        print("Examples:")
        print("  python cleanup.py ong          # cleans ongoing_tweets.json")
        print("  python cleanup.py comm         # cleans comments.json")
        print("  python cleanup.py sim          # cleans simulation_state.json")
        print("  python cleanup.py ong|comm|sim # cleans all three files")
        sys.exit(1)
        
    pattern = sys.argv[1]
    patterns_map = {
        'ong': 'ongoing_tweets.json',
        'comm': 'comments.json',
        'sim': 'simulation_state.json',
        'digest': 'digest_history.json',
        'digest_acti': 'digest_history_acti.json',
        'tech': 'tech_evolution.json'
    }
    
    # Split the pattern by '|' and process each part
    for part in pattern.split('|'):
        part = part.strip()
        if part in patterns_map:
            print(f"\nCleaning up {patterns_map[part]}...")
            cleanup_files(patterns_map[part])
        else:
            print(f"Warning: Unknown pattern '{part}', skipping...") 