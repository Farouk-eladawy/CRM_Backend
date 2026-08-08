expected_count = 6
user_params = ["a", "b", "c", "d"]
comp_params = []
for i in range(expected_count):
    val = user_params[i] if i < len(user_params) and str(user_params[i]).strip() else "-"
    comp_params.append({"type": "text", "text": str(val)})

print(comp_params)
print(len(comp_params))
