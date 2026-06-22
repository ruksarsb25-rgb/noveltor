import { useState, useCallback } from "react";
import { Toaster } from "react-hot-toast";
import toast from "react-hot-toast";

import Header from "./components/Header.jsx";
import RecentDocumentsPanel from "./components/RecentDocumentsPanel.jsx";
import UploadScreen from "./screens/UploadScreen.jsx";
import MetadataScreen from "./screens/MetadataScreen.jsx";
import SectionsScreen from "./screens/SectionsScreen.jsx";
import ExportScreen from "./screens/ExportScreen.jsx";
import AbstractCollectionScreen from "./screens/AbstractCollectionScreen.jsx";

import { defaultArticle, saveDraft, loadDraft } from "./store.js";

const NFP_DEFAULTS = defaultArticle();
const DRAFT = loadDraft();

export default function App() {
  const [step, setStep] = useState(1);
  const [article, setArticle] = useState(DRAFT || defaultArticle());
  const [abstractCollection, setAbstractCollection] = useState(null);
  const [sourceData, setSourceData] = useState(null);

  const handleParsed = useCallback((parsed) => {
    // Abstract collection — go to dedicated screen
    if (parsed.type === "abstract_collection") {
      setAbstractCollection(parsed);
      setStep("abstracts");
      return;
    }

    setArticle((prev) => ({
      ...prev,
      title: parsed.title || prev.title,
      authors: parsed.authors?.length ? parsed.authors : prev.authors,
      abstract: parsed.abstract || prev.abstract,
      keywords: parsed.keywords?.length ? parsed.keywords : prev.keywords,
      sections: parsed.sections || prev.sections,
      references: parsed.references || prev.references,
      figures: parsed.figures || prev.figures,
      journal_name: NFP_DEFAULTS.journal_name,
      publisher_name: NFP_DEFAULTS.publisher_name,
      publisher_loc: NFP_DEFAULTS.publisher_loc,
    }));
    setSourceData(null);
    setStep(2);
  }, []);

  const handleSelectRecentDocument = useCallback((doc) => {
    // Load the recent document's data
    setArticle(doc.data);
    setSourceData(doc.data);
    // Jump to metadata screen
    setStep(2);
    toast.success("Loaded: " + doc.title);
  }, []);

  const handleRegenerateMetadata = useCallback(() => {
    if (!sourceData) {
      toast.error("No source data available");
      return;
    }
    setArticle((prev) => ({
      ...prev,
      title: sourceData.title || prev.title,
      authors: sourceData.authors?.length ? sourceData.authors : prev.authors,
      abstract: sourceData.abstract || prev.abstract,
      keywords: sourceData.keywords?.length ? sourceData.keywords : prev.keywords,
    }));
    toast.success("Metadata regenerated");
  }, [sourceData]);

  const handleSaveDraft = () => {
    saveDraft(article);
    toast.success("Draft saved");
  };

  // Abstract collection mode — bypass normal step flow
  if (step === "abstracts" && abstractCollection) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <Toaster position="top-right" toastOptions={{ className: "text-sm font-medium", duration: 3000 }} />
        <Header currentStep={1} onStepClick={() => {}} onSaveDraft={null} />
        <main className="flex-1">
          <AbstractCollectionScreen
            collection={abstractCollection}
            onReset={() => { setAbstractCollection(null); setStep(1); }}
          />
        </main>
      </div>
    );
  }

  const Screen = {
    1: <UploadScreen onParsed={handleParsed} />,
    2: <MetadataScreen article={article} onChange={setArticle} onNext={() => setStep(3)} onRegenerate={sourceData ? handleRegenerateMetadata : null} />,
    3: <SectionsScreen article={article} onChange={setArticle} onNext={() => setStep(4)} />,
    4: <ExportScreen article={article} />,
  }[step];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Toaster position="top-right" toastOptions={{ className: "text-sm font-medium", duration: 3000 }} />
      <Header currentStep={step} onStepClick={setStep} onSaveDraft={handleSaveDraft} />
      <div className="flex-1 flex">
        <main className="flex-1">{Screen}</main>
        <RecentDocumentsPanel onSelectDocument={handleSelectRecentDocument} />
      </div>
    </div>
  );
}
