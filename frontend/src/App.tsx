import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Overview } from './components/Overview';
import { KnowledgeLayerList } from './components/KnowledgeLayerList';
import { KnowledgeLayerDetail } from './components/KnowledgeLayerDetail';
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
  fetchKnowledgeLayers,
  extractDocumentFacts,
  analyzeRelationships,
  DocumentItem,
  FactItem,
  FactRelationship,
  EvaluationMetrics,
  KnowledgeLayerItem,
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState<
    'overview' | 'knowledge-layers' | 'documents' | 'facts' | 'relationships' | 'evaluation'
  >('knowledge-layers');

  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [selectedKnowledgeLayerId, setSelectedKnowledgeLayerId] = useState<string | null>(null);
  const [isUploaderOpen, setIsUploaderOpen] = useState<boolean>(false);

  const [apiStatus, setApiStatus] = useState<'online' | 'offline' | 'loading'>('loading');
  const [providerName, setProviderName] = useState<string>('Mock');

  const [knowledgeLayers, setKnowledgeLayers] = useState<KnowledgeLayerItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [facts, setFacts] = useState<FactItem[]>([]);
  const [relationships, setRelationships] = useState<FactRelationship[]>([]);
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);

  const loadAllData = async () => {
    try {
      const [klData, docsData, factsData, relsData, metricsData] = await Promise.all([
        fetchKnowledgeLayers().catch(() => []),
        fetchDocuments().catch(() => []),
        fetchFacts().catch(() => []),
        fetchRelationships().catch(() => []),
        fetchEvaluationMetrics().catch(() => null),
      ]);

      setKnowledgeLayers(klData);
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
      await analyzeRelationships();
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
          setSelectedKnowledgeLayerId(null);
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
        ) : selectedKnowledgeLayerId ? (
          <KnowledgeLayerDetail
            knowledgeLayerId={selectedKnowledgeLayerId}
            onBack={() => setSelectedKnowledgeLayerId(null)}
            onSelectDocument={(id) => setSelectedDocumentId(id)}
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
        ) : activeTab === 'knowledge-layers' ? (
          <KnowledgeLayerList
            knowledgeLayers={knowledgeLayers}
            onSelectKnowledgeLayer={(id) => setSelectedKnowledgeLayerId(id)}
            onRefresh={loadAllData}
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
