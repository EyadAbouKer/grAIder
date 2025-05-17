def sum_even(numbers):
    count = 0
    for num in numbers:
        if num % 2 == 0:
            count += 1  # Counts evens rather than summing
    return count