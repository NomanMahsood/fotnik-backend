def generate_inpaint_prompt(product_description: str, target_audience: str, target_photo_description: str | None = None) -> str:
    """
    Generate a prompt string for the ad-inpaint model based on provided inputs.
    
    Args:
        product_description (str): Description of the product
        target_audience (str): Description of the target audience
        target_photo_description (str | None): Optional description of the target photo
        
    Returns:
        str: The formatted prompt string
    """
    base_template = """<purpose>
  You are an expert prompt engineer for the ad-inpaint model on Replicate. Your goal is to generate a highly appealing, realistic product photo by crafting a precise prompt and negative prompt.
</purpose>
<instructions>
  <instruction>
    Consider the provided product image, product description, and target audience description to craft the positive (user-prompt) and negative (user-negative-prompt) prompts.
  </instruction>
  <instruction>
  If target-photo-description is provided, adjust the positive and negative prompt to generate the product photo according to the description.
  </instruction>
  <instruction>
    Align the product seamlessly with the described environment; avoid mentioning people unless explicitly instructed (if the target-photo-description is provided and in the description it is mentioned to include a person or people).
  </instruction>
  <instruction>
    Ensure the prompts deliver a realistic aesthetic that fits the desired style and setting.
  </instruction>
  <instruction>
    Use the examples to understand how to structure both the positive prompt and the negative prompt.
  </instruction>
</instructions>

<product-description>
{product_description}
</product-description>

<target-audience>
{target_audience}
</target-audience>
{target_photo_section}

<examples>
  <example>
    <positive-prompt>
      modern sofa+ in a contemporary living room, filled with stylish decor+;modern, contemporary, sofa, living room, stylish decor
    </positive-prompt>
    <negative-prompt>
      illustration, 3d, sepia, painting, cartoons, sketch, (worst quality:2)
    </negative-prompt>
  </example>
  <example>
    <positive-prompt>
      bottle+ on a wooden platform-, adorned with a beautiful flower+ and surrounded by colorful decorative elements and greenery.
    </positive-prompt>
    <negative-prompt>
      text, watermark, painting, cartoons, sketch, worst quality
    </negative-prompt>
  </example>
  <example>
    <positive-prompt>
      bottle on table for Christmas
    </positive-prompt>
    <negative-prompt>
      illustration, 3d, sepia, painting, cartoons, sketch, (worst quality:2)
    </negative-prompt>
  </example>
</examples>"""

    target_photo_section = f"""
<target-photo-description>
{target_photo_description}
</target-photo-description>""" if target_photo_description and target_photo_description.strip() else ""

    return base_template.format(
        product_description=product_description,
        target_audience=target_audience,
        target_photo_section=target_photo_section
    )
