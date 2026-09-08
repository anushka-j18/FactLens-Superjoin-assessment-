import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Overview } from './components/Overview';
import { DocumentList } from './components/DocumentList';
import { DocumentDetail } from './components/DocumentDetail';
import { FactList } from './components/FactList';
import { RelationshipMatrix } from './components/RelationshipMatrix';
import { EvaluationView } from './components/EvaluationView';
import { DocumentUploaderModal } from './components/DocumentUploaderModal';

import {
  fetchHealth,
  fetchDocuments,
  fetchFacts,
  fetchRelationships,
  fetchEvaluationMetrics,
  extractDocumentFacts,
  analyzeRelationships,
  DocumentItem,
  FactItem,
  FactRelationship,
  EvaluationMetrics,
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'facts' | 'relationships' | 'evaluation'>('overview');
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [isUploaderOpen, setIsUploaderOpen] = useState<boolean>(false);

  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'loading'>('loading');
  const [providerName, setProviderName] = useState<string>('Mock');

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [facts, setFacts] = useState<FactItem[]>([]);
  const [relationships, setRelationships] = useState<FactRelationship[]>([]);
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);

  const loadAllData = async () => {
    try {
      const [docsData, factsData, relsData, metricsData] = await Promise.all([
        fetchDocuments().catch(() => []),
        fetchFacts().catch(() => []),
        fetchRelationships().catch(() => []),
        fetchEvaluationMetrics().catch(() => null),
      ]);

      setDocuments(docsData);
      setFacts(factsData);
      setRelationships(relsData);
      setMetrics(metricsData);
    } catch (err) {
      console.error('Error loading application data:', err);
    }
  };

  useEffect(() => {
    // Check health
    fetchHealth()
      .then((data) => {
        setApiStatus('online');
        setProviderName(data.llm_provider || 'Mock');
      })
      .catch(() => setApiStatus('offline'));

    loadAllData();
  }, []);

  const handleExtractFacts = async (docId: string) => {
    try {
      await extractDocumentFacts(docId);
      await loadAllData();
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    }
  };

  const handleReanalyzeRelationships = async () => {
    try {
      await analyzeRelationships();
      await loadAllData();
    } catch (err: any) {
      alert(`Re-analysis failed: ${err.message}`);
    }
  };

  return (
    <div className="app-layout">
      {/* Top Navbar */}
      <Header
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setSelectedDocumentId(null);
        }}
        onUploadClick={() => setIsUploaderOpen(true)}
        apiStatus={apiStatus}
        providerName={providerName}
      />

      {/* Main Viewport Content */}
      <main className="main-viewport">
        {selectedDocumentId ? (
          <DocumentDetail
            documentId={selectedDocumentId}
            onBack={() => setSelectedDocumentId(null)}
          />
        ) : activeTab === 'overview' ? (
          <Overview
            documents={documents}
            facts={facts}
            relationships={relationships}
            metrics={metrics}
            onNavigateTab={setActiveTab}
            onSelectDocument={(id) => setSelectedDocumentId(id)}
            onSelectFact={() => setActiveTab('facts')}
            onRefresh={loadAllData}
            onUploadClick={() => setIsUploaderOpen(true)}
          />
        ) : activeTab === 'documents' ? (
          <DocumentList
            documents={documents}
            onSelectDocument={(id) => setSelectedDocumentId(id)}
            onExtractFacts={handleExtractFacts}
            onUploadClick={() => setIsUploaderOpen(true)}
          />
        ) : activeTab === 'facts' ? (
          <FactList facts={facts} />
        ) : activeTab === 'relationships' ? (
          <RelationshipMatrix
            relationships={relationships}
            onReanalyze={handleReanalyzeRelationships}
          />
        ) : activeTab === 'evaluation' ? (
          <EvaluationView metrics={metrics} onRefresh={loadAllData} />
        ) : null}
      </main>

      {/* Upload Modal */}
      <DocumentUploaderModal
        isOpen={isUploaderOpen}
        onClose={() => setIsUploaderOpen(false)}
        onUploadSuccess={() => {
          loadAllData();
          setActiveTab('documents');
        }}
      />
    </div>
  );
}
