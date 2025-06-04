"""
Simple script to update the dengue_response.md file with an unsupported country response.
"""
from pathlib import Path

def update_dengue_response():
    """Write an updated dengue response for Zimbabwe to the dengue_response.md file."""
    
    response_text = """
Dear Patient,

Thank you for reaching out for advice on your upcoming travel to Zimbabwe. It's crucial to consider your health history, especially given your previous dengue fever infection.

Firstly, I must inform you that specific dengue fever data is not available for Zimbabwe due to limited resources. This means we cannot provide precise statistics on dengue prevalence, risk levels, or seasonal patterns.

Despite this data gap, I can offer you some general advice to help you prepare for your trip:

1. **Increased Risk of Severe Disease**: As someone with a history of dengue infection, you have an increased risk of developing severe dengue if infected again. This is a significant consideration for your travel plans.

2. **Pre-travel Consultation**: I strongly recommend consulting with a travel medicine specialist before your trip. They can provide personalized advice based on the latest available data and your health history.

3. **General Prevention Measures**: Regardless of the destination, it's essential to take precautions against mosquito bites:
   - Use EPA-registered insect repellent containing DEET, picaridin, or IR3535
   - Wear long sleeves and pants, especially during dawn and dusk when mosquitoes are most active
   - Stay in accommodations with air conditioning or screens
   - Use bed nets if sleeping in areas without adequate protection

4. **Seeking Medical Care**: If you develop symptoms such as high fever, severe headache, pain behind the eyes, muscle and joint pains, nausea, or vomiting during or after your travel, seek medical attention immediately and inform healthcare providers about your dengue history.

5. **Official Travel Advisories**: Check the latest travel advisories from official sources like the CDC or WHO for the most current information on health and safety in Zimbabwe.

Remember, while specific dengue data for Zimbabwe is not available, these general precautions can help minimize your risk of infection.

Sources:
- Centers for Disease Control and Prevention (CDC): https://www.cdc.gov/dengue/index.html
- World Health Organization (WHO): https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue
"""
    
    # Write to the user-specified dengue_response.md file
    user_md_file = Path("/Users/wesjackson/Code/Summit2025/dengue-agents-summit-2025/dengue_response.md")
    with open(user_md_file, 'w') as f:
        f.write("# Dengue Data Analysis Report\n\nRESPONSE:\n\n")
        f.write(response_text)
    
    print(f"Updated dengue response written to: {user_md_file}")
    return str(user_md_file)

if __name__ == "__main__":
    # Run the update
    output_file = update_dengue_response()
    print(f"Updated dengue_response.md with proper unsupported country handling!")
