def sum_even(numbers):
    total = 0
    for x in numbers:
        if x % 2 == 1:  # Checks odd instead of even
            total += x
    return total