import React, { createContext, useContext, useState, ReactNode } from 'react';

interface ScanProgress {
  current: number;
  total: number;
}

interface ScanState {
  isScanning: boolean;
  scanProgress: ScanProgress | null;
  gatewayId: string;
}

type ScanType = 'security' | 'compliance' | 'predictions' | 'optimization';

interface ScanContextType {
  startScan: (type: ScanType, gatewayId: string, total: number) => void;
  updateProgress: (type: ScanType, gatewayId: string, current: number) => void;
  completeScan: (type: ScanType, gatewayId: string) => void;
  getScanStateForPage: (type: ScanType, gatewayId: string | null) => { isScanning: boolean; scanProgress: ScanProgress | null };
}

const ScanContext = createContext<ScanContextType | undefined>(undefined);

export const ScanProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Store multiple concurrent scans: { "security-gateway123": { isScanning, scanProgress }, ... }
  const [scans, setScans] = useState<Record<string, ScanState>>({});

  const getScanKey = (type: ScanType, gatewayId: string) => `${type}-${gatewayId}`;

  const startScan = (type: ScanType, gatewayId: string, total: number) => {
    const key = getScanKey(type, gatewayId);
    setScans(prev => ({
      ...prev,
      [key]: {
        isScanning: true,
        scanProgress: { current: 0, total },
        gatewayId,
      },
    }));
  };

  const updateProgress = (type: ScanType, gatewayId: string, current: number) => {
    const key = getScanKey(type, gatewayId);
    setScans(prev => {
      const scan = prev[key];
      if (!scan) return prev;
      return {
        ...prev,
        [key]: {
          ...scan,
          scanProgress: scan.scanProgress ? { ...scan.scanProgress, current } : null,
        },
      };
    });
  };

  const completeScan = (type: ScanType, gatewayId: string) => {
    const key = getScanKey(type, gatewayId);
    setScans(prev => {
      const newScans = { ...prev };
      delete newScans[key];
      return newScans;
    });
  };

  const getScanStateForPage = (type: ScanType, gatewayId: string | null) => {
    if (!gatewayId) {
      return {
        isScanning: false,
        scanProgress: null,
      };
    }
    
    const key = getScanKey(type, gatewayId);
    const scan = scans[key];
    
    if (scan) {
      return {
        isScanning: scan.isScanning,
        scanProgress: scan.scanProgress,
      };
    }
    
    return {
      isScanning: false,
      scanProgress: null,
    };
  };

  return (
    <ScanContext.Provider value={{ startScan, updateProgress, completeScan, getScanStateForPage }}>
      {children}
    </ScanContext.Provider>
  );
};

export const useScan = () => {
  const context = useContext(ScanContext);
  if (context === undefined) {
    throw new Error('useScan must be used within a ScanProvider');
  }
  return context;
};

// Made with Bob
