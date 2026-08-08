import ai_agent

agent = ai_agent.AIAgent()
sender = "BRUNO Charlyne via GetYourGuide <message@reply.getyourguide.com>"
subject = "Your booking for Hurghada: Luxor Karnak,Hatshepsut & the Valley of the Kings (Karnak + Hatshepsut +Valley of the Kings,Tutankhamun + Meals) - GYGZGZXYNLWF is confirmed! ✨"
body = "• Charlyne Bruno and Nelson Sancey\n• Siva Grand beach\n• 459"

supplier = agent.check_if_supplier_email(sender, subject, body)
print("Supplier:", supplier)

if supplier:
    cls = agent.classify_supplier_email_type(body, subject)
    print("Classification:", cls)

