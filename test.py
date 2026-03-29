from src.genai.memory import RAGMemory

memory = RAGMemory()

memory.add("High queue time caused by staff shortage")

result = memory.retrieve("Why is queue time high?")
print(result)
