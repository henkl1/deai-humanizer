from realshot_naturalizer import humanize_prompt, transform_prompt


def main() -> None:
    simple_prompt = transform_prompt(
        "Portrait of a woman with flawless smooth skin, perfect lighting, "
        "oversaturated colors, perfect symmetry, 8k masterpiece"
    )
    print("Realistic Prompt:")
    print(simple_prompt)

    result = humanize_prompt(
        "Graduation photo of a student in cap and gown, over saturated colors, plastic skin",
        mode="auto",
        intensity=0.8,
    )
    print("\nEdit Instruction:")
    print(result.edit_instruction)


if __name__ == "__main__":
    main()
