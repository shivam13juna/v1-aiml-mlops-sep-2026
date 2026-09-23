def merge_sort_v2(values):
	"""Return a sorted copy of values using the merge sort algorithm."""
	if len(values) <= 1:
		return values[:]

	middle = len(values) // 2
	left = merge_sort_v2(values[:middle])
	right = merge_sort_v2(values[middle:])

	merged = []
	left_index = right_index = 0

	while left_index < len(left) and right_index < len(right):
		if left[left_index] <= right[right_index]:
			merged.append(left[left_index])
			left_index += 1
		else:
			merged.append(right[right_index])
			right_index += 1

	merged.extend(left[left_index:])
	merged.extend(right[right_index:])
	return merged


if __name__ == "__main__":
	numbers = [38, 27, 43, 3, 9, 82, 10]
	print("Before sorting:", numbers)
	print("After sorting: ", merge_sort_v2(numbers))
