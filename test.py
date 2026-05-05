import google.generativeai as genai                       
import os                                                                                                                                                                                                                                
from dotenv import load_dotenv
                            
load_dotenv()                                                                                                                                                                                                                            
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")                                                                                                                                                                                        
print(model.generate_content("Say hello.").text)                                                                                                                                                                                         