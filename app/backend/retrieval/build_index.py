from app.backend.services.rag_service import rag_service

if __name__ == "__main__":
    print("Checking Knowledge Index...")
    rag_service.build_index_if_needed()
    print("Ready.")
