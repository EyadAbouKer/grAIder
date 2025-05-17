def sum_even(numbers)  # Missing colon
    total = 0
    for x in numbers:
        if x % 2 == 0:
            total += x
    return total