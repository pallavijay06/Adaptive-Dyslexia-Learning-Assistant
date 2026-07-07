import { createContext, useContext, useMemo, useState } from 'react';

const DocumentContext = createContext(null);

export function DocumentProvider({ children }) {
  const [activeDocument, setActiveDocument] = useState(null);
  const [documents, setDocuments] = useState([]);

  const value = useMemo(() => ({ activeDocument, setActiveDocument, documents, setDocuments }), [activeDocument, documents]);

  return <DocumentContext.Provider value={value}>{children}</DocumentContext.Provider>;
}

export function useDocument() {
  return useContext(DocumentContext);
}
