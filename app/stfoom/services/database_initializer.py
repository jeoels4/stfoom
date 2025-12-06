"""
Database Initializer
====================
Comprehensive database initialization module that creates all required tables
with full column definitions for STFOOM application.

This module ensures that when the application is first run (or when the database
doesn't exist), a complete database with all necessary tables and columns is created.
"""

import sqlite3
import os
from typing import Dict, List, Tuple
from datetime import datetime

from config.settings import get_db_path
from app.stfoom.services.sync_service import SyncService


class DatabaseInitializer:
    """Handles comprehensive database initialization with all tables and columns."""

    def __init__(self, db_path: str = None):
        """Initialize the database initializer.
        
        Args:
            db_path: Optional path to database file. If not provided, uses default path from path_manager.
        """
        self.db_path = db_path if db_path is not None else get_db_path()
        self.table_definitions = self._get_table_definitions()

    def _get_table_definitions(self) -> Dict[str, str]:
        """Get all table definitions with full column schemas."""
        return {

            'achats': '''
                CREATE TABLE achats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                fournisseur TEXT NOT NULL,
                mt_ht REAL,
                ttc REAL,
                timbre REAL,
                taxes TEXT, -- JSON: list of {name, value}
                notes TEXT,
                paiement_statut TEXT,
                paiement_methode TEXT,
                created_at REAL DEFAULT CURRENT_TIMESTAMP
            , num_facture TEXT, updated_at REAL, fournisseur_alias TEXT, deleted_at REAL DEFAULT 0)
            ''',

            'activity_logs': '''
                CREATE TABLE activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        resource TEXT NOT NULL,
        details TEXT,
        ip_address TEXT,
        timestamp REAL DEFAULT CURRENT_TIMESTAMP,
        success BOOLEAN DEFAULT 1, updated_at REAL, created_at REAL, deleted_at REAL DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
    )
            ''',

            'application_settings': '''
                CREATE TABLE application_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        description TEXT,
                        data_type TEXT DEFAULT 'string',
                        created_at REAL DEFAULT CURRENT_TIMESTAMP,
                        updated_at REAL DEFAULT CURRENT_TIMESTAMP, deleted INTEGER DEFAULT 0,
                        UNIQUE(category, key)
                    )
            ''',

            'avoir_applications': '''
                CREATE TABLE avoir_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bl_id INTEGER NOT NULL,
                avoir_type TEXT NOT NULL,
                is_applied INTEGER DEFAULT 1,
                created_at REAL DEFAULT CURRENT_TIMESTAMP, updated_at REAL, deleted_at REAL DEFAULT 0,
                FOREIGN KEY (bl_id) REFERENCES bon_livraison(id),
                UNIQUE(bl_id, avoir_type)
            )
            ''',

            'avoir_config': '''
                CREATE TABLE avoir_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT UNIQUE NOT NULL,
                rate REAL NOT NULL DEFAULT 0.0,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at REAL DEFAULT CURRENT_TIMESTAMP
            , created_at REAL, deleted_at REAL DEFAULT 0)
            ''',

            'banques': '''
                CREATE TABLE banques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom_banque TEXT NOT NULL,
                numero_compte TEXT UNIQUE,
                solde_initial REAL DEFAULT 0,
                devise TEXT DEFAULT 'TND',
                actif INTEGER DEFAULT 1
            , est_defaut INTEGER DEFAULT 0, updated_at REAL, created_at REAL, deleted_at REAL DEFAULT 0)
            ''',

            'bon_livraison': '''
                CREATE TABLE bon_livraison (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    date_livraison DATE NOT NULL,
                    code_fournisseur TEXT NOT NULL,
                    quantite REAL NOT NULL,
                    montant REAL NOT NULL,
                    unite TEXT DEFAULT 'tonnes',
                    description TEXT,
                    statut TEXT DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'facturee', 'annulee')),
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER, avoir_payment_before_20_days INTEGER DEFAULT 1, avoir_total_factures_200t_month INTEGER DEFAULT 1, avoir_sur_livraison INTEGER DEFAULT 0, avoir_par_annee INTEGER DEFAULT 0, material_id INTEGER, deleted_at REAL DEFAULT 0,
                    FOREIGN KEY (code_fournisseur) REFERENCES fournisseurs (code_fournisseur),
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''',

            'bon_livraison_avoirs': '''
                CREATE TABLE bon_livraison_avoirs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bl_id INTEGER NOT NULL,
                    achat_id INTEGER NOT NULL
                , created_at REAL, updated_at REAL)
            ''',

            'bon_livraison_factures': '''
                CREATE TABLE bon_livraison_factures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bl_id INTEGER NOT NULL,
                    achat_id INTEGER NOT NULL
                , created_at REAL, updated_at REAL)
            ''',

            'caisse_transactions': '''
                CREATE TABLE caisse_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                montant REAL NOT NULL,
                type TEXT NOT NULL, -- 'encaissement' or 'decaissement'
                description TEXT,
                nfacture INTEGER,
                created_at REAL DEFAULT CURRENT_TIMESTAMP
            , num_facture TEXT, updated_at REAL, deleted INTEGER DEFAULT 0, deleted_at REAL DEFAULT 0)
            ''',

            'calendar_events': '''
                CREATE TABLE calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    event_type TEXT,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'active',
                    assigned_to TEXT,
                    related_id TEXT,
                    related_type TEXT,
                    created_at REAL DEFAULT 0,
                    updated_at REAL DEFAULT 0,
                    deleted_at REAL DEFAULT 0,
                    deleted INTEGER DEFAULT 0
                , done INTEGER DEFAULT 0)
            ''',

            'chantier_remises': '''
                CREATE TABLE chantier_remises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chantier_name TEXT NOT NULL,
            product_code TEXT NOT NULL,
            remise_percentage REAL DEFAULT 0,
            prix_specifique REAL DEFAULT 0,
            created_at REAL DEFAULT CURRENT_TIMESTAMP,
            updated_at REAL DEFAULT CURRENT_TIMESTAMP, client_code TEXT,
            UNIQUE(chantier_name, product_code)
        )
            ''',

            'cheque_config': '''
                CREATE TABLE cheque_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    banque_id INTEGER NOT NULL,
                    carne_dernier_numero INTEGER NOT NULL,
                    mini_cheque_alert INTEGER DEFAULT 10,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (banque_id) REFERENCES banques(id),
                    UNIQUE(banque_id)
                )
            ''',

            'cheque_print_layout': '''
                CREATE TABLE cheque_print_layout (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    page_width_mm REAL NOT NULL DEFAULT 175.0,
                    page_height_mm REAL NOT NULL DEFAULT 80.0,
                    montant_number_x REAL, montant_number_y REAL,
                    montant_letters_x REAL, montant_letters_y REAL,
                    beneficiaire_x REAL, beneficiaire_y REAL,
                    date_x REAL, date_y REAL,
                    lieu_x REAL, lieu_y REAL,
                    settings_json TEXT
                , created_at REAL, updated_at REAL)
            ''',

            'cheques': '''
                CREATE TABLE cheques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_cheque INTEGER NOT NULL,
                    banque_id INTEGER NOT NULL,
                    date_cheque DATE NOT NULL,
                    montant REAL NOT NULL,
                    fournisseur TEXT NOT NULL,
                    beneficiaire TEXT,
                    statut TEXT DEFAULT 'emis',  -- 'emis', 'annule', 'encaisse'
                    motif_annulation TEXT,
                    notes TEXT,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP, bank_transaction_id INTEGER, deleted_at REAL DEFAULT 0,
                    FOREIGN KEY (banque_id) REFERENCES banques(id),
                    UNIQUE(numero_cheque, banque_id)
                )
            ''',

            'ciment_facture_bls': '''
                CREATE TABLE ciment_facture_bls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    facture_id INTEGER NOT NULL,
                    bl_id INTEGER NOT NULL,
                    montant_inclus REAL NOT NULL,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP, updated_at REAL,
                    FOREIGN KEY (facture_id) REFERENCES ciment_factures (id) ON DELETE CASCADE,
                    FOREIGN KEY (bl_id) REFERENCES bon_livraison (id) ON DELETE CASCADE,
                    UNIQUE(facture_id, bl_id)
                )
            ''',

            'ciment_factures': '''
                CREATE TABLE ciment_factures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_facture TEXT UNIQUE NOT NULL,
                    date_facture DATE NOT NULL,
                    code_fournisseur TEXT NOT NULL,
                    montant_total REAL NOT NULL,
                    montant_ht REAL NOT NULL,
                    tva REAL DEFAULT 0,
                    statut TEXT DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'payee', 'annulee')),
                    date_echeance DATE,
                    notes TEXT,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (code_fournisseur) REFERENCES fournisseurs (code_fournisseur),
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''',

            'ciment_notif_sent': '''
                CREATE TABLE ciment_notif_sent (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            notif_type TEXT NOT NULL,
                            supplier TEXT NOT NULL,
                            month TEXT NOT NULL,
                            created_at REAL DEFAULT CURRENT_TIMESTAMP, updated_at REAL,
                            UNIQUE(notif_type, supplier, month)
                        )
            ''',

            'clients': '''
                CREATE TABLE "clients" (
        code_client TEXT PRIMARY KEY,
        raison_sociale TEXT,
        adresse TEXT,
        tva TEXT,
        tel TEXT,
        chantier TEXT,
        remise_p001 REAL,
        remise_p002 REAL,
        remise_p003 REAL,
        specific_p001 REAL,
        specific_p002 REAL,
        specific_p003 REAL,
        specific_p004 REAL,
        updated_at REAL,
        created_at REAL,
        deleted_at REAL DEFAULT 0
    )
            ''',

            'devis': '''
                CREATE TABLE devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_number TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            is_grand_tunis BOOLEAN DEFAULT 1,
            total_ht REAL DEFAULT 0.0,
            total_ttc REAL DEFAULT 0.0,
            status TEXT DEFAULT 'draft',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            file_path TEXT,
            notes TEXT
        , client TEXT, deleted_at REAL DEFAULT 0)
            ''',

            'devis_items': '''
                CREATE TABLE devis_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT NOT NULL,
            custom_price REAL,
            quantity INTEGER DEFAULT 1, created_at REAL, updated_at REAL,
            FOREIGN KEY (devis_id) REFERENCES devis (id) ON DELETE CASCADE
        )
            ''',

            'document_access_log': '''
                CREATE TABLE document_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                accessed_by TEXT,
                access_date TEXT DEFAULT CURRENT_TIMESTAMP,
                access_type TEXT,
                ip_address TEXT, created_at REAL, updated_at REAL,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
            ''',

            'document_downloads': '''
                CREATE TABLE document_downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER NOT NULL,
                        downloaded_by TEXT NOT NULL,
                        download_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT, created_at REAL, updated_at REAL,
                        FOREIGN KEY (document_id) REFERENCES documents(id)
                    )
            ''',

            'document_folders': '''
                CREATE TABLE document_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_name TEXT NOT NULL,
                parent_folder_id INTEGER,
                folder_path TEXT NOT NULL,
                created_by TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                description TEXT, created_at REAL, updated_at REAL,
                FOREIGN KEY (parent_folder_id) REFERENCES document_folders (id)
            )
            ''',

            'document_permissions': '''
                CREATE TABLE document_permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER,
                        folder_id INTEGER,
                        user_id TEXT,
                        permission_type TEXT NOT NULL, -- 'read', 'write', 'admin'
                        granted_by TEXT NOT NULL,
                        granted_date TEXT DEFAULT CURRENT_TIMESTAMP, created_at REAL, updated_at REAL,
                        FOREIGN KEY (document_id) REFERENCES documents(id),
                        FOREIGN KEY (folder_id) REFERENCES document_folders(id)
                    )
            ''',

            'documents': '''
                CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_hash TEXT NOT NULL,
                mime_type TEXT,
                folder_id INTEGER,
                uploaded_by TEXT,
                upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                tags TEXT,
                is_public BOOLEAN DEFAULT 0, created_at REAL, updated_at REAL,
                FOREIGN KEY (folder_id) REFERENCES document_folders (id)
            )
            ''',

            'factures': '''
                CREATE TABLE factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_facture TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        date_creation TEXT DEFAULT (datetime('now')),
        date_echeance TEXT,
        statut TEXT DEFAULT 'Brouillon',
        total_ht REAL DEFAULT 0.0,
        total_ttc REAL DEFAULT 0.0,
        created_at REAL DEFAULT (datetime('now')),
        updated_at REAL DEFAULT (datetime('now')), deleted_at REAL DEFAULT 0,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    )
            ''',

            'fournisseurs': '''
                CREATE TABLE fournisseurs (
            code_fournisseur TEXT PRIMARY KEY,
            nom_fournisseur TEXT NOT NULL,
            created_at REAL DEFAULT CURRENT_TIMESTAMP
        , updated_at REAL, id INTEGER, adresse TEXT DEFAULT '', telephone TEXT DEFAULT '', email TEXT DEFAULT '', deleted_at REAL DEFAULT 0)
            ''',

            'materials': '''
                CREATE TABLE materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT 'tonnes',
                    price REAL NOT NULL DEFAULT 0,
                    supplier TEXT,
                    minimum_stock REAL DEFAULT 0,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP
                )
            ''',

            'monthly_avoir_factures': '''
                CREATE TABLE monthly_avoir_factures (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        year_month TEXT NOT NULL,
                        facture_id INTEGER NOT NULL,
                        quantity REAL NOT NULL,
                        avoir_amount REAL DEFAULT 0.0,
                        created_at REAL DEFAULT CURRENT_TIMESTAMP, updated_at REAL,
                        UNIQUE(year_month, facture_id)
                    )
            ''',

            'monthly_avoir_tracking': '''
                CREATE TABLE monthly_avoir_tracking (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        year_month TEXT NOT NULL,
                        total_quantity REAL DEFAULT 0.0,
                        avoir_rate REAL DEFAULT 0.0,
                        total_avoir_amount REAL DEFAULT 0.0,
                        notification_sent INTEGER DEFAULT 0,
                        is_processed INTEGER DEFAULT 0,
                        created_at REAL DEFAULT CURRENT_TIMESTAMP,
                        updated_at REAL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(year_month)
                    )
            ''',

            'paiements_factures': '''
                CREATE TABLE paiements_factures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nfacture INTEGER NOT NULL,
                montant_paye REAL NOT NULL,
                methode_paiement TEXT NOT NULL,  -- 'banque' ou 'caisse'
                date_paiement TEXT NOT NULL,     -- YYYY-MM-DD
                reference_paiement TEXT,         -- Référence bancaire ou numéro de reçu
                notes TEXT,
                created_at REAL DEFAULT CURRENT_TIMESTAMP
            , mode_paiement TEXT, echeance TEXT, banque_id INTEGER, updated_at REAL, deleted INTEGER DEFAULT 0, deleted_at REAL DEFAULT 0)
            ''',

            'payment_methods': '''
                CREATE TABLE payment_methods (
                    key TEXT PRIMARY KEY,
                    label TEXT NOT NULL
                , updated_at REAL, created_at REAL, deleted_at REAL DEFAULT 0)
            ''',

            'permission_types': '''
                CREATE TABLE permission_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    , updated_at REAL, created_at REAL)
            ''',

            'permissions': '''
                CREATE TABLE permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                permission TEXT NOT NULL, allowed INTEGER DEFAULT 0, rank TEXT, resource TEXT, action TEXT, updated_at REAL, created_at REAL,
                UNIQUE(user_id, permission),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            ''',

            'products': '''
                CREATE TABLE "products" (
"code" TEXT,
  "designation" TEXT,
  "unite" TEXT,
  "prix_ht" REAL
, updated_at REAL, created_at REAL, deleted_at REAL DEFAULT 0)
            ''',

            'rank_permissions': '''
                CREATE TABLE rank_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rank TEXT NOT NULL,
                    module TEXT NOT NULL,
                    action TEXT NOT NULL,
                    allowed INTEGER NOT NULL, updated_at REAL, created_at REAL,
                    UNIQUE(rank, module, action)
                )
            ''',

            'ranks': '''
                CREATE TABLE ranks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_system BOOLEAN DEFAULT 0,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP
                , deleted_at REAL DEFAULT 0)
            ''',

            'retenus': '''
                CREATE TABLE retenus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                client TEXT NOT NULL,
                nfacture INTEGER,
                retenu_percent REAL,
                retenu_amount REAL,
                source TEXT NOT NULL, -- 'vente' or 'manuel'
                notes TEXT,
                created_at REAL DEFAULT CURRENT_TIMESTAMP
            , updated_at REAL, party_type TEXT DEFAULT 'client', deleted INTEGER DEFAULT 0, deleted_at REAL DEFAULT 0)
            ''',

            'settings': '''
                CREATE TABLE settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                created_at REAL DEFAULT CURRENT_TIMESTAMP,
                updated_at REAL DEFAULT CURRENT_TIMESTAMP
            )
            ''',

            'sync_metadata': '''
                CREATE TABLE sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL
                )
            ''',

            'sync_tombstones': '''
                CREATE TABLE sync_tombstones (
                table_name TEXT NOT NULL,
                pk_value TEXT NOT NULL,
                deleted_at REAL NOT NULL DEFAULT (datetime('now'))
            )
            ''',

            'system_permissions': '''
                CREATE TABLE system_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    description TEXT,
                    created_at REAL DEFAULT CURRENT_TIMESTAMP,
                    updated_at REAL DEFAULT CURRENT_TIMESTAMP
                , deleted_at REAL DEFAULT 0)
            ''',

            'system_rank_permissions': '''
                CREATE TABLE system_rank_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rank_id INTEGER NOT NULL,
                    permission_id INTEGER NOT NULL,
                    granted_at REAL DEFAULT CURRENT_TIMESTAMP,
                    granted_by TEXT, created_at REAL, updated_at REAL, deleted_at REAL DEFAULT 0,
                    FOREIGN KEY (rank_id) REFERENCES ranks(id) ON DELETE CASCADE,
                    FOREIGN KEY (permission_id) REFERENCES system_permissions(id) ON DELETE CASCADE,
                    UNIQUE(rank_id, permission_id)
                )
            ''',

            'transactions_bancaires': '''
                CREATE TABLE transactions_bancaires (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                banque_id INTEGER NOT NULL,
                date_transaction TEXT NOT NULL,           -- YYYY-MM-DD
                type_transaction TEXT NOT NULL,           -- 'encaissement' ou 'decaissement'
                montant REAL NOT NULL,
                nfacture INTEGER,                         -- Numéro de facture (optionnel)
                nom_client TEXT,                          -- Nom du client/fournisseur
                numero_cheque TEXT,                       -- Numéro de chèque
                description TEXT,
                verifie INTEGER DEFAULT 0,                -- 0 = non vérifié, 1 = vérifié
                date_verification TEXT,                   -- Date de vérification
                created_at REAL DEFAULT CURRENT_TIMESTAMP, mode_paiement TEXT, echeance TEXT, num_facture TEXT, updated_at REAL, deleted INTEGER DEFAULT 0, deleted_at REAL DEFAULT 0,
                FOREIGN KEY (banque_id) REFERENCES banques (id)
            )
            ''',

            'user_sessions': '''
                CREATE TABLE user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_token TEXT UNIQUE NOT NULL,
        created_at REAL DEFAULT CURRENT_TIMESTAMP,
        expires_at REAL NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        is_active BOOLEAN DEFAULT 1, updated_at REAL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
            ''',

            'users': '''
                CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, full_name TEXT NOT NULL, rank TEXT NOT NULL, email TEXT, is_active BOOLEAN DEFAULT 1, created_at REAL DEFAULT CURRENT_TIMESTAMP, last_login REAL, failed_attempts INTEGER DEFAULT 0, locked_until REAL, password_changed_at REAL DEFAULT CURRENT_TIMESTAMP, updated_at REAL, force_password_change BOOLEAN DEFAULT 0, temporary_password BOOLEAN DEFAULT 0, password_reset_token TEXT, password_reset_expires REAL, password TEXT, deleted INTEGER DEFAULT 0, deleted_at REAL DEFAULT 0)
            ''',

            'ventes': '''
                CREATE TABLE ventes (
            nfacture       INTEGER PRIMARY KEY,
            date_facture   TEXT    NOT NULL,
            code_client    TEXT    NOT NULL,
            raison_sociale TEXT    NOT NULL,
            mt_ht_p001     REAL,
            mt_ht_p002     REAL,
            mt_ht_p003     REAL,
            fodec          REAL,
            tva19          REAL,
            transport_p004 REAL,
            tva7           REAL,
            timbre         REAL,
            ttc            REAL
        , details TEXT DEFAULT '', chantier TEXT DEFAULT '', updated_at REAL, nfacture_seq INTEGER, created_at REAL, client_nom TEXT, deleted INTEGER DEFAULT 0, deleted_at REAL DEFAULT 0)
            ''',

            'voitures': '''
                CREATE TABLE voitures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                genre TEXT NOT NULL,
                utilisateur TEXT,
                matricule TEXT UNIQUE NOT NULL,
                date_visite TEXT,
                date_assurance TEXT,
                date_vignette TEXT,
                date_premiere_mise TEXT
            , updated_at REAL, created_at REAL, deleted_at REAL DEFAULT 0)
            ''',
        }


    def initialize_database(self) -> bool:
        """
        Initialize the complete database with all tables and columns.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure database directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create all tables
                for table_name, create_sql in self.table_definitions.items():
                    try:
                        cursor.execute(create_sql)
                        print(f"[DB_INIT] Created table: {table_name}")
                    except sqlite3.OperationalError as e:
                        if "already exists" in str(e).lower():
                            print(f"[DB_INIT] Table already exists: {table_name}")
                        else:
                            print(f"[DB_INIT] Error creating table {table_name}: {e}")
                            return False

                # Create indexes for better performance
                self._create_indexes(cursor)

                # Create triggers for sync tracking (CRITICAL for sync to work!)
                self._create_triggers(cursor)

                # Initialize default data
                self._initialize_default_data(cursor)

                conn.commit()
                
            # After database is created, ensure schema provisioning creates sync triggers
            # This handles tables that don't have triggers in template DB (like clients)
            from app.stfoom.services.schema_provision import ensure_schema_ready
            ensure_schema_ready(db_path=self.db_path)
            
            print("[DB_INIT] Database initialization completed successfully")
            return True

        except Exception as e:
            print(f"[DB_INIT] Database initialization failed: {e}")
            return False

    def _create_indexes(self, cursor):
        """Create indexes for better query performance."""
        # Get existing table schemas to check column existence
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        def column_exists(table_name, column_name):
            if table_name not in tables:
                return False
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                return column_name in columns
            except:
                return False
        
        indexes = [
            # Ventes indexes - check column existence (using correct column names from schema)
            ("ventes", "date_facture", "CREATE INDEX IF NOT EXISTS idx_ventes_date ON ventes(date_facture)"),
            ("ventes", "code_client", "CREATE INDEX IF NOT EXISTS idx_ventes_client ON ventes(code_client)"),
            ("ventes", "nfacture", "CREATE INDEX IF NOT EXISTS idx_ventes_nfacture ON ventes(nfacture)"),

            # Achats indexes - check column existence (using correct column names from schema)
            ("achats", "date", "CREATE INDEX IF NOT EXISTS idx_achats_date ON achats(date)"),
            ("achats", "fournisseur", "CREATE INDEX IF NOT EXISTS idx_achats_fournisseur ON achats(fournisseur)"),
            ("achats", "fournisseur_alias", "CREATE INDEX IF NOT EXISTS idx_achats_fournisseur_alias ON achats(fournisseur_alias)"),

            # Clients indexes - check column existence
            ("clients", "raison_sociale", "CREATE INDEX IF NOT EXISTS idx_clients_raison_sociale ON clients(raison_sociale)"),
            ("clients", "code_client", "CREATE INDEX IF NOT EXISTS idx_clients_code ON clients(code_client)"),

            # Factures indexes - check column existence (using correct column names from schema)
            ("factures", "client_id", "CREATE INDEX IF NOT EXISTS idx_factures_client ON factures(client_id)"),
            ("factures", "date_creation", "CREATE INDEX IF NOT EXISTS idx_factures_date ON factures(date_creation)"),
            ("factures", "statut", "CREATE INDEX IF NOT EXISTS idx_factures_statut ON factures(statut)"),

            # Bank transactions indexes - check column existence
            ("transactions_bancaires", "banque_id", "CREATE INDEX IF NOT EXISTS idx_bank_transactions_banque ON transactions_bancaires(banque_id)"),
            ("transactions_bancaires", "date_transaction", "CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON transactions_bancaires(date_transaction)"),
            ("transactions_bancaires", "type_transaction", "CREATE INDEX IF NOT EXISTS idx_bank_transactions_type ON transactions_bancaires(type_transaction)"),
            ("transactions_bancaires", "verifie", "CREATE INDEX IF NOT EXISTS idx_bank_transactions_verifie ON transactions_bancaires(verifie)"),

            # Caisse transactions indexes - check column existence
            ("caisse_transactions", "date", "CREATE INDEX IF NOT EXISTS idx_caisse_date ON caisse_transactions(date)"),
            ("caisse_transactions", "type", "CREATE INDEX IF NOT EXISTS idx_caisse_type ON caisse_transactions(type)"),

            # Activity logs indexes - check column existence
            ("activity_logs", "user_id", "CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id)"),
            ("activity_logs", "timestamp", "CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp)"),
            ("activity_logs", "action", "CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action)"),

            # Calendar events indexes - check column existence
            ("calendar_events", "start_date", "CREATE INDEX IF NOT EXISTS idx_calendar_start_date ON calendar_events(start_date)"),
            ("calendar_events", "assigned_to", "CREATE INDEX IF NOT EXISTS idx_calendar_assigned_to ON calendar_events(assigned_to)"),

            # Sync tombstones indexes - check column existence
            ("sync_tombstones", "table_name", "CREATE INDEX IF NOT EXISTS idx_sync_tombstones_table ON sync_tombstones(table_name)"),
            ("sync_tombstones", "pk_value", "CREATE INDEX IF NOT EXISTS idx_sync_tombstones_pk ON sync_tombstones(pk_value)"),

            # Cement facture BLs indexes - check column existence
            ("ciment_facture_bls", "facture_id", "CREATE INDEX IF NOT EXISTS idx_ciment_facture_bls_facture ON ciment_facture_bls(facture_id)"),
            ("ciment_facture_bls", "bl_id", "CREATE INDEX IF NOT EXISTS idx_ciment_facture_bls_bl ON ciment_facture_bls(bl_id)"),

            # Rank permissions indexes - check column existence
            ("rank_permissions", "rank", "CREATE INDEX IF NOT EXISTS idx_rank_permissions_rank ON rank_permissions(rank)"),
            ("rank_permissions", "module", "CREATE INDEX IF NOT EXISTS idx_rank_permissions_module ON rank_permissions(module)"),
        ]

        for table_name, column_name, index_sql in indexes:
            try:
                if column_exists(table_name, column_name):
                    cursor.execute(index_sql)
                else:
                    print(f"[DB_INIT] Skipping index for non-existent column {table_name}.{column_name}")
            except Exception as e:
                print(f"[DB_INIT] Warning: Could not create index: {e}")

    def _create_triggers(self, cursor):
        """Create triggers for sync tracking and timestamp management.
        
        Triggers are essential for:
        1. Automatically updating updated_at timestamps when rows change
        2. Creating tombstone records when rows are deleted  
        3. Tracking changes for synchronization between databases
        """
        try:
            # Check if we're initializing a fresh database (no triggers yet)
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'")
            existing_trigger_count = cursor.fetchone()[0]
            
            if existing_trigger_count > 0:
                print(f"[DB_INIT] Triggers already exist ({existing_trigger_count}), skipping trigger creation")
                return
            
            print("[DB_INIT] Creating sync triggers from template database...")
            
            # Get path to the template database (the working local database)
            from app.core.path_manager import get_db_path
            template_db_path = get_db_path()
            
            # If we're initializing the template database itself, skip trigger creation
            # (triggers will be created by sync service initialization)
            if os.path.samefile(self.db_path, template_db_path):
                print("[DB_INIT] Initializing template database, triggers will be created by sync service")
                return
            
            # Read trigger definitions from template database
            import sqlite3
            template_conn = sqlite3.connect(template_db_path)
            template_cursor = template_conn.cursor()
            
            template_cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='trigger' AND sql IS NOT NULL 
                ORDER BY name
            """)
            triggers = template_cursor.fetchall()
            template_conn.close()
            
            if not triggers:
                print("[DB_INIT] Warning: No triggers found in template database")
                return
            
            # Create each trigger in the new database
            created_count = 0
            for trigger_name, trigger_sql in triggers:
                try:
                    cursor.execute(trigger_sql)
                    created_count += 1
                except Exception as e:
                    print(f"[DB_INIT] Warning: Could not create trigger {trigger_name}: {e}")
            
            print(f"[DB_INIT] Created {created_count}/{len(triggers)} triggers successfully")
            
            # Create CASCADE DELETE triggers for referential integrity
            print("[DB_INIT] Creating CASCADE DELETE triggers for referential integrity...")
            try:
                # Trigger for ranks table - auto-delete orphaned system_rank_permissions
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS trg_ranks_cascade_delete
                    AFTER DELETE ON ranks
                    FOR EACH ROW
                    BEGIN
                        DELETE FROM system_rank_permissions WHERE rank_id = OLD.id;
                    END
                """)
                
                # Trigger for system_permissions table - auto-delete orphaned system_rank_permissions
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS trg_system_permissions_cascade_delete
                    AFTER DELETE ON system_permissions
                    FOR EACH ROW
                    BEGIN
                        DELETE FROM system_rank_permissions WHERE permission_id = OLD.id;
                    END
                """)
                
                print("[DB_INIT] CASCADE DELETE triggers created successfully")
            except Exception as e:
                print(f"[DB_INIT] Warning: Could not create CASCADE DELETE triggers: {e}")
            
        except Exception as e:
            print(f"[DB_INIT] Warning: Trigger creation failed: {e}")
            # Don't fail initialization if trigger creation fails
            # Triggers can be created later by sync service if needed

    def _initialize_default_data(self, cursor):
        """Initialize default data for the database."""
        try:
            # Initialize default payment methods
            default_payment_methods = [
                ('especes', '💵 Espèces'),
                ('cheque', '🧾 Chèque'),
                ('virement', '💳 Virement'),
                ('virement_interne', '🔄 Virement Interne (Banque ↔ Caisse)'),
                ('traite', '📄 Traite'),
                ('cb', '💳 Carte bancaire'),
                ('prelevement', '🔄 Prélèvement')
            ]

            cursor.executemany('''
                INSERT OR IGNORE INTO payment_methods (key, label, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', [(key, label, datetime.now().timestamp(), datetime.now().timestamp())
                  for key, label in default_payment_methods])

            # Initialize default ranks (without 'level' column as it doesn't exist in schema)
            default_ranks = [
                ('admin', 'Administrateur'),
                ('manager', 'Gestionnaire'),
                ('operator', 'Opérateur'),
                ('viewer', 'Observateur'),
                ('guest', 'Invité')
            ]

            cursor.executemany('''
                INSERT OR IGNORE INTO ranks (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            ''', [(name, desc, datetime.now().timestamp(), datetime.now().timestamp())
                  for name, desc in default_ranks])

            # Initialize default permissions - COMPLETE SET (91 permissions)
            # This matches the full local database to ensure server DB is created with all permissions
            default_permissions = [
                ('factures.view', 'Voir la page Factures', 'page'),
                ('factures.create', 'Créer des factures', 'page'),
                ('factures.edit', 'Modifier des factures', 'page'),
                ('factures.delete', 'Supprimer des factures', 'page'),
                ('devis.view', 'Voir la page Devis', 'page'),
                ('devis.create', 'Créer des devis', 'page'),
                ('calendar.view', 'Voir le calendrier', 'page'),
                ('users.manage', 'Gérer les utilisateurs', 'system'),
                ('permissions.manage', 'Gérer les permissions', 'system'),
                ('backup.create', 'Créer des sauvegardes', 'system'),
                ('settings.view', 'Voir les paramètres', 'system'),
                ('settings.update', 'Modifier les paramètres', 'system'),
                ('special.access', 'Special access to restricted features', 'system'),
                ('calculator.view', 'Accéder à la calculatrice', 'page'),
                ('vente.view', 'Accéder à la page Ventes', 'page'),
                ('achat.view', 'Accéder à la page Achats', 'page'),
                ('ciment.view', 'Accéder aux matières premières', 'page'),
                ('documents.view', 'Accéder aux documents', 'page'),
                ('voiture.view', 'Accéder aux véhicules', 'page'),
                ('bank.view', 'Accéder à la banque', 'page'),
                ('caisse.view', 'Accéder à la caisse', 'page'),
                ('retenu.view', 'Accéder aux retenus', 'page'),
                ('sync.view', 'Accéder à la synchronisation', 'page'),
                ('backup.view', 'Accéder aux sauvegardes', 'page'),
                ('factures.export', 'Exporter des factures', 'data'),
                ('devis.edit', 'Modifier des devis', 'data'),
                ('devis.delete', 'Supprimer des devis', 'data'),
                ('bank.delete', 'Supprimer des transactions bancaires', 'page'),
                ('vente.create', 'Créer des ventes', 'data'),
                ('vente.edit', 'Modifier des ventes', 'data'),
                ('vente.delete', 'Supprimer des ventes', 'data'),
                ('vente.export', 'Exporter des ventes', 'data'),
                ('achat.create', 'Créer des achats', 'data'),
                ('achat.edit', 'Modifier des achats', 'data'),
                ('caisse.edit', 'Modifier des transactions de caisse', 'page'),
                ('caisse.delete', 'Supprimer des transactions de caisse', 'page'),
                ('documents.upload', 'Télécharger des documents', 'data'),
                ('documents.download', 'Télécharger des documents', 'data'),
                ('documents.delete', 'Supprimer des documents', 'data'),
                ('calendar.create', 'Créer des événements', 'data'),
                ('calendar.edit', 'Modifier des événements', 'data'),
                ('calendar.delete', 'Supprimer des événements', 'data'),
                ('voiture.create', 'Ajouter des véhicules', 'data'),
                ('voiture.edit', 'Modifier des véhicules', 'data'),
                ('voiture.delete', 'Supprimer des véhicules', 'data'),
                ('backup.restore', 'Restaurer des sauvegardes', 'system'),
                ('bank.edit', 'Modifier des transactions bancaires', 'data'),
                ('sync.execute', 'Exécuter la synchronisation', 'system'),
                ('caisse.create', 'Ajouter des opérations de caisse', 'data'),
                ('settings.edit', 'Modifier les paramètres', 'system'),
                ('users.view', 'Voir la gestion des utilisateurs', 'admin'),
                ('users.create', 'Créer des utilisateurs', 'admin'),
                ('users.edit', 'Modifier des utilisateurs', 'admin'),
                ('users.delete', 'Supprimer des utilisateurs', 'admin'),
                ('permissions.view', 'Voir la gestion des permissions', 'admin'),
                ('logs.view', 'Voir les logs système', 'system'),
                ('bank.verify', 'Vérifier des transactions bancaires', 'data'),
                ('cheque.view', 'Voir la page Gestion des Chèques', 'page'),
                ('cheque.create', 'Créer des chèques', 'data'),
                ('cheque.edit', 'Modifier des chèques', 'data'),
                ('cheque.delete', 'Supprimer des chèques', 'data'),
                ('cheque.print', 'Imprimer des chèques', 'action'),
                ('retenu.create', 'Créer des retenus', 'data'),
                ('retenu.edit', 'Modifier des retenus', 'data'),
                ('retenu.delete', 'Supprimer des retenus', 'data'),
                ('ciment.create', 'Créer des achats de ciment', 'data'),
                ('ciment.edit', 'Modifier des achats de ciment', 'data'),
                ('ciment.delete', 'Supprimer des achats de ciment', 'data'),
                ('monthly_avoir.view', 'Voir les avoirs mensuels', 'page'),
                ('vente.update', 'Mettre à jour des ventes', 'data'),
                ('achat.update', 'Mettre à jour des achats', 'data'),
                ('bank.update', 'Mettre à jour des transactions bancaires', 'data'),
                ('clients.view', 'Voir les clients', 'page'),
                ('clients.create', 'Créer des clients', 'data'),
                ('clients.edit', 'Modifier des clients', 'data'),
                ('clients.delete', 'Supprimer des clients', 'data'),
                ('fournisseurs.view', 'Voir les fournisseurs', 'page'),
                ('fournisseurs.create', 'Créer des fournisseurs', 'data'),
                ('fournisseurs.edit', 'Modifier des fournisseurs', 'data'),
                ('fournisseurs.delete', 'Supprimer des fournisseurs', 'data'),
                ('stock.view', 'Voir le stock', 'page'),
                ('stock.create', 'Créer des articles', 'data'),
                ('stock.edit', 'Modifier des articles', 'data'),
                ('stock.delete', 'Supprimer des articles', 'data'),
                ('loyer.view', 'Voir la page Loyer', 'page'),
                ('loyer.create', 'Créer des loyers', 'data'),
                ('loyer.edit', 'Modifier des loyers', 'data'),
                ('loyer.delete', 'Supprimer des loyers', 'data'),
                ('loyer.export', 'Exporter des loyers', 'data'),
                ('achat.delete', 'Supprimer des achats', 'data'),
                ('bank.create', 'Créer des transactions bancaires', 'data'),
            ]

            cursor.executemany('''
                INSERT OR IGNORE INTO system_permissions (name, description, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', [(name, desc, cat, datetime.now().timestamp(), datetime.now().timestamp())
                  for name, desc, cat in default_permissions])

            # Initialize default rank permissions (admin gets all permissions)
            # First, get admin rank_id
            cursor.execute('SELECT id FROM ranks WHERE name = ?', ('admin',))
            admin_rank_row = cursor.fetchone()
            
            if admin_rank_row:
                admin_rank_id = admin_rank_row[0]
                # Get all permission IDs from system_permissions
                cursor.execute('SELECT id FROM system_permissions')
                permission_ids = [row[0] for row in cursor.fetchall()]
                
                # Grant all permissions to admin rank
                for perm_id in permission_ids:
                    cursor.execute('''
                        INSERT OR IGNORE INTO system_rank_permissions (rank_id, permission_id, granted_by, granted_at, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (admin_rank_id, perm_id, 'system', datetime.now().timestamp(),
                          datetime.now().timestamp(), datetime.now().timestamp()))

            # Initialize sync metadata - force full sync on first run
            cursor.execute('''
                INSERT OR IGNORE INTO sync_metadata (key, value, updated_at)
                VALUES ('force_full_sync', '1', ?)
            ''', (datetime.now().timestamp(),))

            print("[DB_INIT] Default data initialized")

        except Exception as e:
            print(f"[DB_INIT] Warning: Could not initialize default data: {e}")

    def ensure_database_exists(self) -> bool:
        """
        Ensure the database exists and is properly initialized.
        This is the main entry point called during application startup.

        Returns:
            bool: True if database exists/is created successfully, False otherwise
        """
        if not os.path.exists(self.db_path):
            print(f"[DB_INIT] Database does not exist, creating: {self.db_path}")
            return self.initialize_database()
        else:
            print(f"[DB_INIT] Database already exists: {self.db_path}")
            # Even if database exists, ensure all tables are present (for updates)
            return self._ensure_all_tables_exist()

    def _ensure_all_tables_exist(self) -> bool:
        """
        Ensure all required tables exist in an existing database.
        This handles cases where the database exists but might be missing some tables.

        Returns:
            bool: True if all tables exist, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Run schema migrations first
                self._run_schema_migrations(cursor)

                # Get existing tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cursor.fetchall()}

                # Create missing tables
                for table_name, create_sql in self.table_definitions.items():
                    if table_name not in existing_tables:
                        try:
                            cursor.execute(create_sql)
                            print(f"[DB_INIT] Created missing table: {table_name}")
                        except Exception as e:
                            print(f"[DB_INIT] Error creating missing table {table_name}: {e}")
                            return False

                # Create indexes if needed
                self._create_indexes(cursor)

                # Create triggers if needed (CRITICAL for sync!)
                self._create_triggers(cursor)

                conn.commit()
                print("[DB_INIT] All tables verified/created successfully")
                return True

        except Exception as e:
            print(f"[DB_INIT] Error ensuring tables exist: {e}")
            return False

    def initialize_server_database(self) -> bool:
        """
        Initialize the server database at the configured server path.
        Creates the same database structure as the local database.
        This is called when server path is configured and database doesn't exist there.

        Returns:
            bool: True if server database was created successfully or already exists, False on error
        """
        try:
            from app.config.settings import settings
            
            server_dir = settings.get_server_path()
            
            if not server_dir or server_dir.strip() == '':
                print("[DB_INIT] No server path configured, skipping server database initialization")
                return True  # Not an error, just no server path configured
            
            # Server path is a DIRECTORY - append database filename
            server_path = os.path.join(server_dir, "stfoom.db")
            
            # Check if server directory is accessible
            if not os.path.exists(server_dir):
                try:
                    os.makedirs(server_dir, exist_ok=True)
                    print(f"[DB_INIT] Created server directory: {server_dir}")
                except Exception as e:
                    print(f"[DB_INIT] Cannot create server directory {server_dir}: {e}")
                    print("[DB_INIT] Server may be offline or path not accessible - skipping server database initialization")
                    return True  # Not a critical error, server might be offline
            
            # Check if server database file already exists and is valid
            if os.path.exists(server_path):
                # Verify it has tables (not empty/corrupted)
                try:
                    import sqlite3
                    conn = sqlite3.connect(server_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    table_count = cursor.fetchone()[0]
                    conn.close()
                    
                    if table_count >= 45:  # Should have at least 45 tables
                        print(f"[DB_INIT] Server database already exists with {table_count} tables: {server_path}")
                        return True
                    else:
                        print(f"[DB_INIT] Server database exists but only has {table_count} tables (expected >=45)")
                        print(f"[DB_INIT] Recreating server database...")
                        os.remove(server_path)
                except Exception as e:
                    print(f"[DB_INIT] Server database exists but appears corrupted: {e}")
                    print(f"[DB_INIT] Recreating server database...")
                    try:
                        os.remove(server_path)
                    except:
                        pass
            
            print(f"[DB_INIT] Initializing server database at: {server_path}")
            
            # Create a temporary database initializer with server path
            original_db_path = self.db_path
            try:
                self.db_path = server_path
                result = self.initialize_database()
                if result:
                    print(f"[DB_INIT] ✓ Server database created successfully at: {server_path}")
                else:
                    print(f"[DB_INIT] ✗ Failed to create server database at: {server_path}")
                return result
            finally:
                # Restore original db_path
                self.db_path = original_db_path
                
        except ImportError:
            print("[DB_INIT] Warning: Could not import Settings for server database initialization")
            return True  # Not critical
        except Exception as e:
            print(f"[DB_INIT] Error initializing server database: {e}")
            return True  # Don't fail application startup if server DB can't be created

    def _run_schema_migrations(self, cursor) -> None:
        """
        Run schema migrations to fix constraint issues between server and client.
        
        This is called on every startup to ensure the local schema matches the server.
        SQLite doesn't support ALTER TABLE DROP CONSTRAINT, so we need to recreate tables.
        """
        print("[DB_INIT] Running schema migrations...")
        
        # List of tables to migrate: (table_name, patterns_to_check)
        # Check if any NOT NULL exists in columns that server might have NULL values
        tables_to_migrate = [
            ('fournisseurs', ['raison_sociale TEXT NOT NULL']),
            ('clients', ['raison_sociale TEXT NOT NULL']),
            ('achats', ['produit TEXT NOT NULL']),
            ('ventes', ['client_nom TEXT NOT NULL', 'produit TEXT NOT NULL', 
                       'quantite REAL NOT NULL', 'prix_unitaire REAL NOT NULL', 'total REAL NOT NULL']),
            ('factures', ['nfacture TEXT NOT NULL']),
            ('devis', ['ndevis TEXT NOT NULL']),
            ('bon_livraison', ['numero_bl TEXT NOT NULL']),
            ('avoir_config', ['type_avoir TEXT NOT NULL']),
            ('voitures', ['marque TEXT NOT NULL']),
            ('system_rank_permissions', ['rank_name TEXT NOT NULL', 'permission_name TEXT NOT NULL'])
        ]
        
        for table_name, patterns_to_check in tables_to_migrate:
            try:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                if cursor.fetchone():
                    # Check if table has the old schema with NOT NULL
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                    result = cursor.fetchone()
                    if result:
                        schema = result[0]
                        
                        # Check if any of the patterns match (indicating migration needed)
                        needs_migration = any(pattern in schema for pattern in patterns_to_check)
                        
                        if needs_migration:
                            print(f"[DB_INIT] Migrating {table_name} table to remove NOT NULL constraints...")
                            
                            # Step 1: Rename old table
                            cursor.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old")
                            
                            # Step 2: Create new table without NOT NULL
                            cursor.execute(self.table_definitions[table_name])
                            
                            # Step 3: Copy data from old table to new
                            cursor.execute(f"""
                                INSERT INTO {table_name} 
                                SELECT * FROM {table_name}_old
                            """)
                            
                            # Step 4: Drop old table
                            cursor.execute(f"DROP TABLE {table_name}_old")
                            
                            print(f"[DB_INIT] Successfully migrated {table_name} table")
            
            except Exception as e:
                print(f"[DB_INIT] Warning: Schema migration error for {table_name} (non-fatal): {e}")


# Global instance for easy access
database_initializer = DatabaseInitializer()


def initialize_database() -> bool:
    """
    Convenience function to initialize the database.
    This is the main entry point for database initialization.

    Returns:
        bool: True if successful, False otherwise
    """
    return database_initializer.ensure_database_exists()


def initialize_server_database() -> bool:
    """
    Convenience function to initialize the server database.
    Creates the same database structure at the configured server path.

    Returns:
        bool: True if successful or server path not configured, False on critical error
    """
    return database_initializer.initialize_server_database()


if __name__ == '__main__':
    print("[DB_INIT] Running database initializer as script")
    
    # Initialize local database
    success = initialize_database()
    if success:
        print("[DB_INIT] ✓ Local database initialization completed successfully")
    else:
        print("[DB_INIT] ✗ Local database initialization failed")
        import sys
        sys.exit(1)
    
    # Initialize server database if configured
    print("\n[DB_INIT] Checking for server database initialization...")
    server_success = initialize_server_database()
    if server_success:
        print("[DB_INIT] ✓ Server database check/initialization completed")
    else:
        print("[DB_INIT] ⚠ Server database initialization had issues (non-critical)")
    
    print("\n[DB_INIT] ✓ All database initialization tasks completed")