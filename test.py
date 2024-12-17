# import os

# script_path = r"D:\relive-debugger\test_script.py"  # Replace with your script path

# # Check if the file exists and is readable
# if os.path.exists(script_path):
#     print(f"File exists: {script_path}")
#     if os.access(script_path, os.R_OK):
#         print(f"File is readable: {script_path}")
#     else:
#         print(f"File is not readable: {script_path}")
# else:
#     print(f"File does not exist: {script_path}")


import os

def test_file_accessibility(script_path):
    try:
        # Check if the file exists
        if not os.path.exists(script_path):
            print(f"File does not exist: {script_path}")
            return False
        
        # Check if the file is readable
        if not os.access(script_path, os.R_OK):
            print(f"File is not readable: {script_path}")
            return False
        
        # Try opening the file
        with open(script_path, 'r') as file:
            print(f"File opened successfully: {script_path}")
            return True

    except Exception as e:
        print(f"Error while accessing the file: {str(e)}")
        return False

# Call the test function with the script path
test_file_accessibility("D:/relive-debugger/test_script.py")
