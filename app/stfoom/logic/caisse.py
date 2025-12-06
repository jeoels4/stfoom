# Temporary stub for caisse module during Phase 3A cleanup

def get_transactions():
    return []

def get_solde():
    return 0.0

def get_resume_periode():
    return {"entrees": 0.0, "sorties": 0.0}

def supprimer_transaction(transaction_id):
    print(f"Warning: Using caisse temporary stub delete {transaction_id} - use CaisseService instead")
    return False

def ajouter_transaction(montant, date_str, type_, desc, nfacture):
    print("Warning: Using caisse temporary stub insert - use CaisseService instead")
    return False
