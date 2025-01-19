def calculate_factorial(n):
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    if n == 0 or n == 1:
        return 1
    return n * calculate_factorial(n - 1)

def find_max_in_list(lst):
    """Find the maximum number in a list."""
    if not lst:
        raise ValueError("List is empty.")
    max_value = lst[0]
    for num in lst:
        if num > max_value:
            max_value = num
    return max_value

def main():
    print("Debugging Test Script")
    
    # Test 1: Debugging Loops
    numbers = [10, 20, 30, 40, 50]
    sum_of_numbers = 0
    for i, num in enumerate(numbers):
        print(f"Adding index {i}, value {num}")
        sum_of_numbers += num
    print(f"Total sum: {sum_of_numbers}")
    
    # Test 2: Debugging Functions
    try:
        print("Factorial of 5:", calculate_factorial(5))
        print("Factorial of -1 (should raise an error):", calculate_factorial(-1))
    except ValueError as e:
        print(f"Error encountered: {e}")
    
    # Test 3: Debugging Conditionals
    test_list = [3, 5, 7, 2, 8]
    print(f"The maximum value in {test_list} is {find_max_in_list(test_list)}")
    try:
        print("Testing empty list (should raise an error):", find_max_in_list([]))
    except ValueError as e:
        print(f"Error encountered: {e}")
    
    # Test 4: Debugging Logical Errors
    user_input = "5"
    print(f"User input: {user_input}")
    squared = int(user_input) ** 2
    print(f"Square of {user_input}: {squared}")
    
if __name__ == "__main__":
    main()
