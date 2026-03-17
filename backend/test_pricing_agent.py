from core.pdf_pipeline.agents import PricingAgent

agent = PricingAgent()

try:
    res = agent.extract_data("dummy md", b"%PDF-1.7\ntest\n%%EOF")
    print("Success:", res)
except Exception as e:
    print("FAILED!")
    print(repr(e))
