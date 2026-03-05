# WDD PulseX Seeding & Runtime Management

.PHONY: seed reset-runtime help

help:
	@echo "Usage:"
	@echo "  make seed           - Generate PalmX-grade seed data"
	@echo "  make reset-runtime  - Clear runtime data and re-seed"
	@echo "  make kb-clean       - Clean and normalize KnowledgeBase"
	@echo "  make kb-validate    - Validate KnowledgeBase integrity"
	@echo "  make kb-refresh     - Clean then Validate"

seed:
	@echo "Refining seed data..."
	python3 scripts/seed_leads.py

reset-runtime:
	@echo "Resetting runtime files..."
	rm -rf runtime/leads/*.csv
	rm -rf runtime/sessions.csv
	$(MAKE) seed

kb-clean:
	@echo "Cleaning KnowledgeBase..."
	python3 scripts/clean_kb.py

kb-validate:
	@echo "Validating KnowledgeBase..."
	python3 scripts/validate_kb.py

kb-refresh: kb-clean kb-validate
	@echo "KB Refresh Complete."
