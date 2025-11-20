# backend/app/services/elasticsearch_service.py - Servicio de búsqueda con Elasticsearch

import logging
from typing import Dict, List, Any, Optional
from elasticsearch import Elasticsearch, NotFoundError
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ElasticsearchService:
    """Servicio de búsqueda de texto completo con Elasticsearch para documentos judiciales"""
    
    def __init__(self):
        self.es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.es = None
        self.connected = False
        
        try:
            # Optional security: basic auth or API key
            es_username = os.getenv('ELASTICSEARCH_USERNAME')
            es_password = os.getenv('ELASTICSEARCH_PASSWORD')
            es_api_key = os.getenv('ELASTICSEARCH_API_KEY')
            
            if es_api_key:
                self.es = Elasticsearch(self.es_url, api_key=es_api_key, request_timeout=30)
            elif es_username and es_password:
                self.es = Elasticsearch(self.es_url, basic_auth=(es_username, es_password), request_timeout=30)
            else:
                self.es = Elasticsearch(self.es_url, request_timeout=30)
            
            self.connected = self.es.ping()
            if self.connected:
                logger.info(f"✅ Connected to Elasticsearch at {self.es_url}")
            else:
                logger.warning(f"⚠️ Elasticsearch at {self.es_url} not available")
        except Exception as e:
            logger.warning(f"⚠️ Elasticsearch connection failed: {e}")
            self.connected = False
    
    def create_indices(self):
        """Crear índices con configuración multi-idioma para árabe, francés y español"""
        if not self.connected:
            logger.warning("Elasticsearch not connected, skipping index creation")
            return False
        
        try:
            # Índice para documentos con análisis multi-idioma
            documents_index = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "arabic_analyzer": {
                                "type": "standard",
                                "stopwords": "_arabic_"
                            },
                            "french_analyzer": {
                                "type": "standard",
                                "stopwords": "_french_"
                            },
                            "spanish_analyzer": {
                                "type": "standard",
                                "stopwords": "_spanish_"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "document_id": {"type": "integer"},
                        "filename": {"type": "text"},
                        "ocr_text": {
                            "type": "text",
                            "fields": {
                                "arabic": {
                                    "type": "text",
                                    "analyzer": "arabic_analyzer"
                                },
                                "french": {
                                    "type": "text",
                                    "analyzer": "french_analyzer"
                                },
                                "spanish": {
                                    "type": "text",
                                    "analyzer": "spanish_analyzer"
                                }
                            }
                        },
                        "ocr_language": {"type": "keyword"},
                        "ocr_confidence": {"type": "integer"},
                        "case_id": {"type": "integer"},
                        "uploaded_by": {"type": "integer"},
                        "indexed_at": {"type": "date"},
                        "is_searchable": {"type": "boolean"}
                    }
                }
            }
            
            # Índice para casos
            cases_index = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "multilang_analyzer": {
                                "type": "standard",
                                "stopwords": ["_arabic_", "_french_", "_spanish_"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "case_id": {"type": "integer"},
                        "case_number": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "multilang_analyzer"
                        },
                        "description": {
                            "type": "text",
                            "analyzer": "multilang_analyzer"
                        },
                        "status": {"type": "keyword"},
                        "owner_id": {"type": "integer"},
                        "assigned_judge_id": {"type": "integer"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            }
            
            # Crear índice de documentos
            if not self.es.indices.exists(index="judicial_documents"):
                self.es.indices.create(index="judicial_documents", body=documents_index)
                logger.info("✅ Created 'judicial_documents' index")
            
            # Crear índice de casos
            if not self.es.indices.exists(index="judicial_cases"):
                self.es.indices.create(index="judicial_cases", body=cases_index)
                logger.info("✅ Created 'judicial_cases' index")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create indices: {e}")
            return False
    
    def index_document(self, document_data: Dict[str, Any]) -> bool:
        """Indexar un documento en Elasticsearch"""
        if not self.connected:
            logger.warning("Elasticsearch not connected, skipping indexing")
            return False
        
        try:
            doc_id = document_data.get('document_id')
            index_body = {
                'document_id': doc_id,
                'filename': document_data.get('filename', ''),
                'ocr_text': document_data.get('ocr_text', ''),
                'ocr_language': document_data.get('ocr_language', 'es'),
                'ocr_confidence': document_data.get('ocr_confidence', 0),
                'case_id': document_data.get('case_id'),
                'uploaded_by': document_data.get('uploaded_by'),
                'indexed_at': datetime.utcnow().isoformat(),
                'is_searchable': document_data.get('is_searchable', True)
            }
            
            self.es.index(
                index='judicial_documents',
                id=doc_id,
                document=index_body
            )
            
            logger.info(f"✅ Indexed document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False
    
    def index_case(self, case_data: Dict[str, Any]) -> bool:
        """Indexar un caso en Elasticsearch"""
        if not self.connected:
            logger.warning("Elasticsearch not connected, skipping indexing")
            return False
        
        try:
            case_id = case_data.get('case_id')
            index_body = {
                'case_id': case_id,
                'case_number': case_data.get('case_number', ''),
                'title': case_data.get('title', ''),
                'description': case_data.get('description', ''),
                'status': case_data.get('status', 'pending'),
                'owner_id': case_data.get('owner_id'),
                'assigned_judge_id': case_data.get('assigned_judge_id'),
                'created_at': case_data.get('created_at', datetime.utcnow()).isoformat(),
                'updated_at': case_data.get('updated_at', datetime.utcnow()).isoformat()
            }
            
            self.es.index(
                index='judicial_cases',
                id=case_id,
                document=index_body
            )
            
            logger.info(f"✅ Indexed case {case_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index case: {e}")
            return False
    
    def search_documents(
        self, 
        query: str, 
        case_id: Optional[int] = None,
        language: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Buscar documentos por texto"""
        if not self.connected:
            logger.warning("Elasticsearch not connected, returning empty results")
            return []
        
        try:
            # Construir query
            must_clauses = []
            
            # Query de texto con multi-match en todos los idiomas
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "ocr_text^3",
                            "ocr_text.arabic^2",
                            "ocr_text.french^2",
                            "ocr_text.spanish^2",
                            "filename^1.5"
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                })
            
            # Filtrar por caso
            if case_id:
                must_clauses.append({"term": {"case_id": case_id}})
            
            # Filtrar por idioma
            if language:
                must_clauses.append({"term": {"ocr_language": language}})
            
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                },
                "size": limit,
                "highlight": {
                    "fields": {
                        "ocr_text": {},
                        "ocr_text.arabic": {},
                        "ocr_text.french": {},
                        "ocr_text.spanish": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            }
            
            response = self.es.search(index="judicial_documents", body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['score'] = hit['_score']
                if 'highlight' in hit:
                    result['highlights'] = hit['highlight']
                results.append(result)
            
            logger.info(f"Found {len(results)} documents for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Document search failed: {e}")
            return []
    
    def search_cases(
        self,
        query: str,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Buscar casos por texto"""
        if not self.connected:
            logger.warning("Elasticsearch not connected, returning empty results")
            return []
        
        try:
            must_clauses = []
            
            # Query de texto
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "description^2", "case_number^2"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                })
            
            # Filtrar por estado
            if status:
                must_clauses.append({"term": {"status": status}})
            
            search_body = {
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                },
                "size": limit,
                "highlight": {
                    "fields": {
                        "title": {},
                        "description": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            }
            
            response = self.es.search(index="judicial_cases", body=search_body)
            
            results = []
            for hit in response['hits']['hits']:
                result = hit['_source']
                result['score'] = hit['_score']
                if 'highlight' in hit:
                    result['highlights'] = hit['highlight']
                results.append(result)
            
            logger.info(f"Found {len(results)} cases for query: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Case search failed: {e}")
            return []
    
    def delete_document(self, document_id: int) -> bool:
        """Eliminar documento del índice"""
        if not self.connected:
            return False
        
        try:
            self.es.delete(index='judicial_documents', id=document_id)
            logger.info(f"Deleted document {document_id} from index")
            return True
        except NotFoundError:
            logger.warning(f"Document {document_id} not found in index")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    def delete_case(self, case_id: int) -> bool:
        """Eliminar caso del índice"""
        if not self.connected:
            return False
        
        try:
            self.es.delete(index='judicial_cases', id=case_id)
            logger.info(f"Deleted case {case_id} from index")
            return True
        except NotFoundError:
            logger.warning(f"Case {case_id} not found in index")
            return False
        except Exception as e:
            logger.error(f"Failed to delete case: {e}")
            return False

# Singleton instance
_es_service = None

def get_elasticsearch_service() -> ElasticsearchService:
    """Obtener instancia singleton del servicio de Elasticsearch"""
    global _es_service
    if _es_service is None:
        _es_service = ElasticsearchService()
        _es_service.create_indices()
    return _es_service
