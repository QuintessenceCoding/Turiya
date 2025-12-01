from sns2f_framework.memory.memory_manager import MemoryManager

mm = MemoryManager()

# Teach it 3 distinct facts that share a property
print("Injecting animals...")
mm.add_symbolic_fact("Lion", "eats", "meat")
mm.add_symbolic_fact("Tiger", "eats", "meat")
mm.add_symbolic_fact("Wolf", "eats", "meat")
# Optional: Ensure they are concepts so edges can form
mm.create_concept("Lion", "A big cat", mm.compressor.embed("Lion"))
mm.create_concept("Tiger", "A big cat", mm.compressor.embed("Tiger"))
mm.create_concept("Wolf", "A canine", mm.compressor.embed("Wolf"))

print("Done.")