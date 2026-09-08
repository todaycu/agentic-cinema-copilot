import { create } from 'zustand';
import { Mission, AgentState, Citation, ApprovalRequest, TaskStep } from '../types';

interface AppState {
  mission: Mission | null;
  activeAgents: Record<string, AgentState>;
  citations: Citation[];
  interrupt: ApprovalRequest | null;
  messages: { id: string; timestamp: number; text: string; role?: string; type: 'info' | 'success' | 'warning' | 'error' }[];
  isConnected: boolean;
  
  // Actions
  startMission: (objective: string) => void;
  resetMission: () => void;
  setConnected: (status: boolean) => void;
  updateMission: (updates: Partial<Mission>) => void;
  updateAgent: (id: string, updates: Partial<AgentState>) => void;
  addCitation: (citation: Citation) => void;
  setInterrupt: (request: ApprovalRequest | null) => void;
  addMessage: (text: string, role?: string, type?: 'info' | 'success' | 'warning' | 'error') => void;
  updateTaskStep: (stepId: string, status: TaskStep['status']) => void;
}

export const useMissionStore = create<AppState>((set) => ({
  mission: null,
  activeAgents: {},
  citations: [],
  interrupt: null,
  messages: [],
  isConnected: false,

  startMission: (objective) => set({
    mission: {
      id: Date.now().toString(),
      objective,
      status: 'planning',
      plan: [],
      startTime: Date.now()
    },
    activeAgents: {},
    citations: [],
    interrupt: null,
    isConnected: false,
    messages: [{ id: Date.now().toString(), timestamp: Date.now(), text: `Mission started: ${objective}`, type: 'info' }]
  }),

  resetMission: () => set({
    mission: null,
    activeAgents: {},
    citations: [],
    interrupt: null,
    isConnected: false,
    messages: []
  }),

  setConnected: (status) => set({ isConnected: status }),

  updateMission: (updates) => set((state) => ({
    mission: state.mission ? { ...state.mission, ...updates } : null
  })),

  updateAgent: (id, updates) => set((state) => ({
    activeAgents: {
      ...state.activeAgents,
      [id]: {
        ...(state.activeAgents[id] || { id, name: 'Agent', role: 'analyst', status: 'idle', thoughtStream: [], toolsCalledCount: 0 }),
        ...updates,
        thoughtStream: updates.thoughtStream 
          ? [...(state.activeAgents[id]?.thoughtStream || []), ...updates.thoughtStream].slice(-4) 
          : state.activeAgents[id]?.thoughtStream || []
      }
    }
  })),

  addCitation: (citation) => set((state) => ({
    citations: [citation, ...state.citations]
  })),

  setInterrupt: (request) => set({ interrupt: request }),

  addMessage: (text, role, type = 'info') => set((state) => ({
    messages: [...state.messages, { id: Date.now().toString() + Math.random(), timestamp: Date.now(), text, role, type }]
  })),

  updateTaskStep: (stepId, status) => set((state) => ({
    mission: state.mission ? {
      ...state.mission,
      plan: state.mission.plan.map(step => step.id === stepId ? { ...step, status } : step)
    } : null
  }))
}));
