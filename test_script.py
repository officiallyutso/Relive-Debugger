def func1():
    print("In func1")
    x = 10
    y = 20
    return x + y

def func2():
    print("In func2")
    a = 5
    b = 10
    return a * b

def main():
    print("Starting program execution.")
    result1 = func1()
    result2 = func2()
    print(f"Results: {result1}, {result2}")

if __name__ == "__main__":
    main()
