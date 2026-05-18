import { useState, useCallback } from "react";
import { Toaster } from "react-hot-toast";
import toast from "react-hot-toast";

import Header from "./components/Header.jsx";
import UploadScreen from "./screens/UploadScreen.jsx";
import MetadataScreen from "./screens/MetadataScreen.jsx";
import SectionsScreen from "./screens/SectionsScreen.jsx";
import ExportScreen from "./screens/ExportScreen.jsx";

import { defaultArticle, saveDraft, loadDraft, sectionBodyText } from "./store.js";

const NFP_DEFAULTS = defaultArticle();

const DRAFT = loadDraft();

export default function App() {
  const [step, setStep] = useState(1);
  const [article, setArticle] = useState(DRAFT || defaultArticle());

  const handleParsed = useCallback((parsed) => {
    setArticle((prev) => ({
      ...prev,
      title: parsed.title || prev.title,
      authors: parsed.authors?.length ? parsed.authors : prev.authors,
      abstract: parsed.abstract || prev.abstract,
      keywords: parsed.keywords?.length ? parsed.keywords : prev.keywords,
      sections: parsed.sections || prev.sections,
      references: parsed.references || prev.references,
      figures: parsed.figures || prev.figures,
      // Journal identity is never inferred from manuscript — always reset to NFP defaults
      journal_name: NFP_DEFAULTS.journal_name,
      publisher_name: NFP_DEFAULTS.publisher_name,
      publisher_loc: NFP_DEFAULTS.publisher_loc,
    }));
    setStep(2);
  }, []);

  const handleSaveDraft = () => {
    saveDraft(article);
    toast.success("Draft saved");
  };

  const Screen = {
    1: <UploadScreen onParsed={handleParsed} />,
    2: (
      <MetadataScreen
        article={article}
        onChange={setArticle}
        onNext={() => setStep(3)}
      />
    ),
    3: (
      <SectionsScreen
        article={article}
        onChange={setArticle}
        onNext={() => setStep(4)}
      />
    ),
    4: <ExportScreen article={article} />,
  }[step];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Toaster
        position="top-right"
        toastOptions={{
          className: "text-sm font-medium",
          duration: 3000,
        }}
      />
      <Header
        currentStep={step}
        onStepClick={setStep}
        onSaveDraft={handleSaveDraft}
      />
      <main className="flex-1">{Screen}</main>
    </div>
  );
}
