import os
import shutil
import time
import gc
import json

def cleanup_temp_data(max_retries=3, delay=1.0):
    """
    Clean up temporary RAG data with retry logic for Windows file locking.
    
    Args:
        max_retries: Number of retry attempts for locked files
        delay: Seconds to wait between retries
    """
    
    # Force garbage collection to release file handles
    gc.collect()
    time.sleep(0.5)  # Give OS time to release handles
    
    cleanup_targets = [
        ("data/pdfs", "folder", "PDF folder"),
        ("papers/*.json", "json_in_folder", "JSON files in papers folder"),
        ("chunk_embeddings.json", "file", "embeddings JSON file"),
        ("chunk_embeddings", "file", "embeddings file (no extension)"),  # fallback if no .json extension
    ]
    
    failed_cleanups = []
    
    for target_path, target_type, description in cleanup_targets:
        success = False
        
        for attempt in range(max_retries):
            try:
                # Handle JSON files in folder
                if target_type == "json_in_folder":
                    folder = target_path.split("/*")[0]
                    if not os.path.exists(folder):
                        print(f"⏭️  {description} - folder doesn't exist")
                        success = True
                        break
                    
                    # Find and delete all JSON files in the folder
                    json_files = [f for f in os.listdir(folder) if f.endswith('.json')]
                    
                    if not json_files:
                        print(f"⏭️  {description} - no JSON files found")
                        success = True
                        break
                    
                    deleted_count = 0
                    for json_file in json_files:
                        json_path = os.path.join(folder, json_file)
                        try:
                            os.chmod(json_path, 0o777)  # Make writable
                            os.remove(json_path)
                            deleted_count += 1
                        except Exception as e:
                            print(f"    ⚠️ Could not delete {json_file}: {e}")
                    
                    print(f"🗑️  Deleted {deleted_count} JSON file(s) from papers folder")
                    success = True
                    break
                
                # Handle regular file
                elif target_type == "file":
                    if not os.path.exists(target_path):
                        # Skip silently if file doesn't exist (one of the extensions will work)
                        success = True
                        break
                    
                    os.chmod(target_path, 0o777)  # Make writable
                    os.remove(target_path)
                    print(f"🗑️  Deleted {description}")
                    success = True
                    break
                
                # Handle folder
                elif target_type == "folder":
                    if not os.path.exists(target_path):
                        print(f"⏭️  {description} already deleted or doesn't exist")
                        success = True
                        break
                    
                    def handle_remove_error(func, path, exc_info):
                        """Try to make file writable and retry deletion"""
                        try:
                            os.chmod(path, 0o777)
                            func(path)
                        except Exception as e:
                            print(f"    ⚠️ Could not delete: {path} ({e})")
                    
                    shutil.rmtree(target_path, onerror=handle_remove_error)
                    print(f"🗑️  Deleted {description}")
                    success = True
                    break
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    print(f"⏳ {description} locked, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    failed_cleanups.append((description, str(e)))
                    
            except Exception as e:
                # Only add to failed if it's not just a "file doesn't exist" case
                if not ("cannot find" in str(e).lower() or "no such file" in str(e).lower()):
                    failed_cleanups.append((description, str(e)))
                break
        
        # Don't double-report failures
        if not success and not any(desc == description for desc, _ in failed_cleanups):
            # Check if file actually still exists before reporting failure
            if target_type == "file" and os.path.exists(target_path):
                failed_cleanups.append((description, "Unknown error"))
            elif target_type == "folder" and os.path.exists(target_path):
                failed_cleanups.append((description, "Unknown error"))
    
    # Summary
    if not failed_cleanups:
        print("\n🧹 Cleanup completed successfully.")
    else:
        print("\n⚠️  Cleanup completed with errors:")
        for desc, error in failed_cleanups:
            print(f"   • {desc}: {error}")
        print("\n💡 Tip: Close any PDF viewers or processes using these files, then retry.")
    
    return len(failed_cleanups) == 0


def release_file_handles():
    """
    Force Python to release all file handles.
    Call this right before cleanup_temp_data().
    """
    gc.collect()  # Run garbage collector
    time.sleep(0.2)  # Let OS process handle releases



    