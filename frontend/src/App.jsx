import { useState, useRef, useEffect } from "react";
import {
  Send,
  Plus,
  Trash2,
  Settings,
  Menu,
  X,
  Copy,
  Download,
  Search,
  Clock,
  AlertCircle,
  CheckCircle,
  Zap,
  ChevronDown,
  Code,
  MessageCircle,
  Brain,
  Workflow,
  Cpu,
  BarChart3,
  Key,
  Sliders,
  Save,
  Play,
  Pause,
  RotateCcw,
  Eye,
  Target,
  GitBranch,
  Terminal,
  Database,
  Shield,
  Moon,
  Sun,
  BookOpen,
  Layers,
  FileText,
  Lightbulb,
  TrendingUp,
  Lock,
  Unlock,
  RefreshCw,
  ArrowRight,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/cjs/styles/prism";

export default function App() {
  // ===== CORE STATE =====
  const [sidebarTab, setSidebarTab] = useState("chats");
  const [query, setQuery] = useState("");
  const [sessions, setSessions] = useState({});
  const [currentSession, setCurrentSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTraces, setExpandedTraces] = useState({});
  const [theme, setTheme] = useState("dark");
  const [sessionTitle, setSessionTitle] = useState("");
  
  // ===== MEMORY SYSTEM =====
  const [longTermMemory, setLongTermMemory] = useState([]);
  const [conversationMemory, setConversationMemory] = useState({});
  const [memoryKey, setMemoryKey] = useState("");
  const [memoryValue, setMemoryValue] = useState("");
  
  // ===== AGENTIC AI STATE =====
  const [workflows, setWorkflows] = useState([]);
  const [agents, setAgents] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [agentMode, setAgentMode] = useState("chat");
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentReflections, setAgentReflections] = useState({});
  
  // ===== RAG & KNOWLEDGE BASE =====
  const [documents, setDocuments] = useState([]);
  const [embeddings, setEmbeddings] = useState([]);
  const [knowledgeBase, setKnowledgeBase] = useState([]);
  const [retrievedDocs, setRetrievedDocs] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  
  // ===== TOOLS & INTEGRATIONS =====
  const [tools, setTools] = useState([]);
  const [toolOutput, setToolOutput] = useState(null);
  const [apiConnections, setApiConnections] = useState([]);
  const [databaseConnections, setDatabaseConnections] = useState([]);
  
  // ===== SETTINGS =====
  const [settings, setSettings] = useState({
    apiKey: "",
    model: "gpt-4",
    temperature: 0.7,
    maxTokens: 2000,
    rateLimit: 100,
    enableMemory: true,
    enableRAG: true,
    enableReflection: true,
    memoryRetention: 100,
  });

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  // Auto-scroll
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [sessions]);

  // Initialize agents with reflection
  useEffect(() => {
    if (agents.length === 0) {
      const defaultAgents = [
        {
          id: 1,
          name: "Planner",
          role: "Strategic planning and task decomposition",
          status: "active",
          executions: 234,
          reflection: "Breaking down complex tasks into manageable steps",
        },
        {
          id: 2,
          name: "Executor",
          role: "Task execution and tool orchestration",
          status: "active",
          executions: 567,
          reflection: "Executing tasks with tool integration",
        },
        {
          id: 3,
          name: "Analyzer",
          role: "RAG-based analysis and data insights",
          status: "active",
          executions: 412,
          reflection: "Analyzing with retrieved knowledge",
        },
        {
          id: 4,
          name: "Critic",
          role: "Quality assurance and reflection",
          status: "active",
          executions: 189,
          reflection: "Reviewing and improving previous outputs",
        },
      ];
      setAgents(defaultAgents);
      defaultAgents.forEach((agent) => {
        setAgentReflections((prev) => ({
          ...prev,
          [agent.id]: [],
        }));
      });
    }
  }, []);

  // Initialize sample tools
  useEffect(() => {
    if (tools.length === 0) {
      setTools([
        {
          id: 1,
          name: "Web Search",
          description: "Search the internet for information",
          status: "active",
        },
        {
          id: 2,
          name: "Database Query",
          description: "Query SQL databases",
          status: "active",
        },
        {
          id: 3,
          name: "API Call",
          description: "Make HTTP requests to APIs",
          status: "active",
        },
        {
          id: 4,
          name: "File Operations",
          description: "Read/write files",
          status: "active",
        },
        {
          id: 5,
          name: "Code Execution",
          description: "Execute Python/JS code",
          status: "active",
        },
      ]);
    }
  }, []);

  // ===== SESSION MANAGEMENT =====
  const createNewSession = () => {
    const id = "session-" + Date.now();
    const title = `Chat ${Object.keys(sessions).length + 1}`;
    setSessions((prev) => ({
      ...prev,
      [id]: {
        messages: [],
        title,
        createdAt: new Date(),
        memory: [],
        retrievedDocs: [],
      },
    }));
    setCurrentSession(id);
    setSessionTitle(title);
    setConversationMemory((prev) => ({
      ...prev,
      [id]: [],
    }));
  };

  const deleteSession = (id) => {
    setSessions((prev) => {
      const updated = { ...prev };
      delete updated[id];
      return updated;
    });
    if (currentSession === id) {
      const remaining = Object.keys(sessions).filter((k) => k !== id);
      setCurrentSession(remaining[0] || null);
    }
  };

  // ===== MEMORY FUNCTIONS =====
  const addToMemory = (key, value) => {
    setLongTermMemory((prev) => [
      ...prev,
      {
        id: Date.now(),
        key,
        value,
        timestamp: new Date(),
        importance: "medium",
      },
    ]);
  };

  const addConversationMemory = (sessionId, memory) => {
    setConversationMemory((prev) => ({
      ...prev,
      [sessionId]: [
        ...(prev[sessionId] || []),
        {
          id: Date.now(),
          ...memory,
          timestamp: new Date(),
        },
      ],
    }));
  };

  // ===== RAG FUNCTIONS =====
  const handleDocumentUpload = async (e) => {
    const files = Array.from(e.target.files);
    setUploadProgress(0);

    for (let index = 0; index < files.length; index++) {
      const file = files[index];
      const docId = Date.now() + index;

      setDocuments((prev) => [
        ...prev,
        {
          id: docId,
          name: file.name,
          type: file.type,
          size: file.size,
          uploadedAt: new Date(),
          chunks: Math.ceil(file.size / 1024),
          summary: null,
        },
      ]);

      // Advanced: call backend summarize endpoint for uploaded doc
      try {
        const formData = new FormData();
        formData.append("file", file);

        const res = await fetch("http://127.0.0.1:8000/api/analysis/upload-and-summarize", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const summaryResult = await res.json();

          const summaryItem = {
            id: docId,
            name: file.name,
            summary: summaryResult.summary || "No summary generated",
          };

          setRetrievedDocs((prev) => [...prev, summaryItem]);

          setDocuments((prev) =>
            prev.map((doc) =>
              doc.id === docId ? { ...doc, summary: summaryItem.summary } : doc
            )
          );
        } else {
          console.error("Summarization API error", await res.text());
        }
      } catch (err) {
        console.error("Failed to summarize document", err);
      }

      setUploadProgress(((index + 1) / files.length) * 100);
    }

    // Keep completed indicator visible briefly, then hide
    setUploadProgress(100);
    setTimeout(() => setUploadProgress(0), 1200);
  };

  const retrieveFromKnowledge = (query) => {
    // Simulated retrieval
    const results = documents.filter(
      (doc) =>
        doc.name.toLowerCase().includes(query.toLowerCase()) ||
        query.toLowerCase().includes(doc.name.toLowerCase())
    );
    setRetrievedDocs(results);
    return results;
  };

  // ===== AGENT REFLECTION =====
  const addAgentReflection = (agentId, reflection) => {
    setAgentReflections((prev) => ({
      ...prev,
      [agentId]: [
        ...(prev[agentId] || []),
        {
          id: Date.now(),
          text: reflection,
          timestamp: new Date(),
          type: "learning",
        },
      ],
    }));
  };

  const currentData = sessions[currentSession] || { messages: [], title: "New Chat" };
  const messages = currentData.messages || [];

  // ===== SEND QUERY WITH FULL FEATURES =====
  const sendQuery = async () => {
    if (!query.trim() || !currentSession) return;

    // Retrieve relevant docs from RAG if enabled
    let ragContext = [];
    if (settings.enableRAG) {
      ragContext = retrieveFromKnowledge(query);
    }

    // Add to conversation memory
    if (settings.enableMemory) {
      addConversationMemory(currentSession, {
        type: "user_query",
        content: query,
        context: ragContext,
      });
    }

    const updatedMessages = [
      ...messages,
      {
        role: "user",
        content: query,
        timestamp: new Date(),
        agentMode,
        memory: conversationMemory[currentSession],
        ragDocs: ragContext,
      },
      {
        role: "assistant",
        content: "",
        trace: [],
        timestamp: new Date(),
        agentMode,
        reflection: null,
      },
    ];

    setSessions((prev) => ({
      ...prev,
      [currentSession]: { ...prev[currentSession], messages: updatedMessages },
    }));

    setLoading(true);
    let fullText = "";

    try {
      const res = await fetch("http://127.0.0.1:8000/run-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          session_id: currentSession,
          agent_mode: agentMode,
          memory: conversationMemory[currentSession],
          rag_context: ragContext,
          tools_available: tools.map((t) => t.name),
          enable_reflection: settings.enableReflection,
        }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        const chunk = decoder.decode(value);
        fullText += chunk;

        setSessions((prev) => {
          const updated = [...prev[currentSession].messages];
          updated[updated.length - 1].content = fullText;
          return {
            ...prev,
            [currentSession]: { ...prev[currentSession], messages: updated },
          };
        });
      }

      // Get advanced trace with reflection
      const traceRes = await fetch("http://127.0.0.1:8000/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          session_id: currentSession,
          agent_mode: agentMode,
          enable_reflection: settings.enableReflection,
        }),
      });

      const traceData = await traceRes.json();

      setSessions((prev) => {
        const updated = [...prev[currentSession].messages];
        updated[updated.length - 1].trace = traceData.agent_trace || [];
        updated[updated.length - 1].reflection = traceData.reflection || null;
        return {
          ...prev,
          [currentSession]: { ...prev[currentSession], messages: updated },
        };
      });

      // Store reflection if enabled
      if (settings.enableReflection && traceData.reflection) {
        addAgentReflection(
          selectedAgent?.id || 1,
          traceData.reflection
        );
      }

      // Add to long-term memory
      if (settings.enableMemory) {
        addToMemory(`session_${currentSession}_q`, query);
        addToMemory(`session_${currentSession}_a`, fullText.substring(0, 200));
      }
    } catch (err) {
      console.error(err);
      setSessions((prev) => {
        const updated = [...prev[currentSession].messages];
        updated[updated.length - 1].content = `Error: ${err.message}`;
        return {
          ...prev,
          [currentSession]: { ...prev[currentSession], messages: updated },
        };
      });
    }

    setLoading(false);
    setQuery("");
    inputRef.current?.focus();
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const exportChat = () => {
    const chatContent = messages
      .map((m) => `${m.role.toUpperCase()}: ${m.content}`)
      .join("\n\n");
    const element = document.createElement("a");
    element.setAttribute(
      "href",
      "data:text/plain;charset=utf-8," + encodeURIComponent(chatContent)
    );
    element.setAttribute("download", `${currentData.title}.txt`);
    element.style.display = "none";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const filteredSessions = Object.entries(sessions).filter(([, data]) =>
    data.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div
      className={`flex h-screen ${
        theme === "dark" ? "bg-slate-950 text-white" : "bg-white text-slate-900"
      }`}
    >
      {/* ===== SIDEBAR ===== */}
      <div
        className={`${
          sidebarOpen ? "w-80" : "w-0"
        } transition-all duration-300 ${
          theme === "dark" ? "bg-slate-900 border-slate-800" : "bg-slate-50 border-slate-200"
        } border-r flex flex-col overflow-hidden`}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-800">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-bold">AI Automation</h1>
          </div>

          {/* Tab Buttons */}
          <div className="flex flex-wrap gap-2 mb-4">
            <button
              onClick={() => setSidebarTab("chats")}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                sidebarTab === "chats"
                  ? "bg-blue-600 text-white"
                  : theme === "dark"
                  ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  : "bg-slate-200 hover:bg-slate-300"
              }`}
            >
              <MessageCircle size={12} className="inline mr-1" />
              Chats
            </button>
            <button
              onClick={() => setSidebarTab("agents")}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                sidebarTab === "agents"
                  ? "bg-blue-600 text-white"
                  : theme === "dark"
                  ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  : "bg-slate-200 hover:bg-slate-300"
              }`}
            >
              <Cpu size={12} className="inline mr-1" />
              Agents
            </button>
            <button
              onClick={() => setSidebarTab("memory")}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                sidebarTab === "memory"
                  ? "bg-blue-600 text-white"
                  : theme === "dark"
                  ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  : "bg-slate-200 hover:bg-slate-300"
              }`}
            >
              <BookOpen size={12} className="inline mr-1" />
              Memory
            </button>
            <button
              onClick={() => setSidebarTab("rag")}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                sidebarTab === "rag"
                  ? "bg-blue-600 text-white"
                  : theme === "dark"
                  ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  : "bg-slate-200 hover:bg-slate-300"
              }`}
            >
              <Layers size={12} className="inline mr-1" />
              RAG
            </button>
            <button
              onClick={() => setSidebarTab("tools")}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition ${
                sidebarTab === "tools"
                  ? "bg-blue-600 text-white"
                  : theme === "dark"
                  ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  : "bg-slate-200 hover:bg-slate-300"
              }`}
            >
              <Zap size={12} className="inline mr-1" />
              Tools
            </button>
          </div>
          
          <button
            onClick={createNewSession}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 p-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition text-sm"
          >
            <Plus size={18} />
            New Chat
          </button>
        </div>

        {/* CHATS TAB */}
        {sidebarTab === "chats" && (
          <>
            <div className="p-4 border-b border-slate-800">
              <div
                className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
                  theme === "dark" ? "bg-slate-800" : "bg-slate-200"
                }`}
              >
                <Search size={16} className="text-slate-500" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`flex-1 outline-none text-sm ${
                    theme === "dark"
                      ? "bg-slate-800 text-white"
                      : "bg-slate-200 text-slate-900"
                  }`}
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {filteredSessions.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <MessageCircle size={28} className="mx-auto mb-2 opacity-50" />
                  <p className="text-xs">No chats</p>
                </div>
              ) : (
                filteredSessions.map(([id, data]) => (
                  <div
                    key={id}
                    className={`group p-3 rounded-lg cursor-pointer transition ${
                      id === currentSession
                        ? theme === "dark"
                          ? "bg-blue-600"
                          : "bg-blue-100"
                        : theme === "dark"
                        ? "hover:bg-slate-800"
                        : "hover:bg-slate-100"
                    }`}
                    onClick={() => setCurrentSession(id)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold truncate text-sm">
                          {data.title}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {data.messages.length} messages
                        </p>
                      </div>
                      <Trash2
                        size={14}
                        className="opacity-0 group-hover:opacity-100 transition text-red-500 cursor-pointer"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession(id);
                        }}
                      />
                    </div>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {/* AGENTS TAB */}
        {sidebarTab === "agents" && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {agents.map((agent) => (
              <div
                key={agent.id}
                onClick={() => setSelectedAgent(agent)}
                className={`p-3 rounded-lg cursor-pointer transition border ${
                  selectedAgent?.id === agent.id
                    ? theme === "dark"
                      ? "bg-purple-600 border-purple-500"
                      : "bg-purple-100 border-purple-400"
                    : theme === "dark"
                    ? "hover:bg-slate-800 border-slate-700"
                    : "hover:bg-slate-100 border-slate-300"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="font-semibold text-sm">{agent.name}</p>
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
                <p className="text-xs text-slate-400 mb-1">{agent.role}</p>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{agent.executions} executions</span>
                  {agentReflections[agent.id]?.length > 0 && (
                    <Lightbulb size={12} className="text-yellow-500" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* MEMORY TAB */}
        {sidebarTab === "memory" && (
          <>
            <div className="p-4 border-b border-slate-800">
              <p className="text-xs font-semibold mb-2">Add Memory</p>
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="Key..."
                  value={memoryKey}
                  onChange={(e) => setMemoryKey(e.target.value)}
                  className={`w-full p-2 rounded text-xs outline-none ${
                    theme === "dark"
                      ? "bg-slate-800 text-white"
                      : "bg-slate-100 text-slate-900"
                  }`}
                />
                <textarea
                  placeholder="Value..."
                  value={memoryValue}
                  onChange={(e) => setMemoryValue(e.target.value)}
                  className={`w-full p-2 rounded text-xs outline-none resize-none ${
                    theme === "dark"
                      ? "bg-slate-800 text-white"
                      : "bg-slate-100 text-slate-900"
                  }`}
                  rows="2"
                />
                <button
                  onClick={() => {
                    if (memoryKey && memoryValue) {
                      addToMemory(memoryKey, memoryValue);
                      setMemoryKey("");
                      setMemoryValue("");
                    }
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700 p-2 rounded text-xs font-semibold transition"
                >
                  Save
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {longTermMemory.length === 0 ? (
                <p className="text-center text-xs text-slate-500 py-4">
                  No memories yet
                </p>
              ) : (
                longTermMemory.map((mem) => (
                  <div
                    key={mem.id}
                    className={`p-3 rounded-lg border ${
                      theme === "dark"
                        ? "bg-slate-800 border-slate-700"
                        : "bg-slate-100 border-slate-300"
                    }`}
                  >
                    <p className="font-semibold text-xs">{mem.key}</p>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                      {mem.value}
                    </p>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {/* RAG TAB */}
        {sidebarTab === "rag" && (
          <>
            <div className="p-4 border-b border-slate-800">
              <p className="text-xs font-semibold mb-2">Upload Documents</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="w-full bg-green-600 hover:bg-green-700 p-2 rounded text-xs font-semibold transition"
              >
                <FileText size={14} className="inline mr-1" />
                Upload
              </button>
              {(uploadProgress > 0 && uploadProgress <= 100) && (
                <div className="mt-2">
                  <div className="w-full bg-slate-700 rounded h-1">
                    <div
                      className="bg-green-500 h-1 rounded"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    {uploadProgress < 100 ? `${Math.round(uploadProgress)}% uploading` : "Upload complete"}
                  </p>
                </div>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {documents.length === 0 ? (
                <p className="text-center text-xs text-slate-500 py-4">
                  No documents
                </p>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    className={`p-3 rounded-lg border ${
                      theme === "dark"
                        ? "bg-slate-800 border-slate-700"
                        : "bg-slate-100 border-slate-300"
                    }`}
                  >
                    <p className="font-semibold text-xs truncate">{doc.name}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {doc.chunks} chunks
                    </p>
                    {doc.summary && (
                      <p className="text-xs text-slate-200 mt-2">Summary: {doc.summary}</p>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Retrieved Docs / Summaries */}
            {(retrievedDocs.length > 0 || documents.some((d) => d.summary)) && (
              <>
                <div className="p-4 border-t border-slate-800 bg-slate-900">
                  <p className="text-xs font-semibold text-green-400 mb-2">📚 Summaries Generated</p>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {(retrievedDocs.length > 0 ? retrievedDocs : documents.filter((d) => d.summary)).map((doc) => (
                    <div
                      key={doc.id}
                      className={`p-3 rounded-lg border ${
                        theme === "dark"
                          ? "bg-green-900/20 border-green-700/30"
                          : "bg-green-100 border-green-300"
                      }`}
                    >
                      <p className="font-semibold text-xs truncate text-green-400 mb-2">{doc.name}</p>
                      <p className="text-xs text-slate-300">{doc.summary}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {/* TOOLS TAB */}
        {sidebarTab === "tools" && (
          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {tools.map((tool) => (
              <div
                key={tool.id}
                className={`p-3 rounded-lg border ${
                  theme === "dark"
                    ? "bg-slate-800 border-slate-700 hover:bg-slate-700"
                    : "bg-slate-100 border-slate-300 hover:bg-slate-200"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="font-semibold text-xs">{tool.name}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {tool.description}
                    </p>
                  </div>
                  <div className="w-2 h-2 bg-green-500 rounded-full ml-2"></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Settings Button */}
        <div className="p-4 border-t border-slate-800">
          <button
            onClick={() => setShowSettings(true)}
            className={`w-full p-3 rounded-lg flex items-center justify-center gap-2 transition text-sm ${
              theme === "dark"
                ? "hover:bg-slate-800"
                : "hover:bg-slate-100"
            }`}
          >
            <Settings size={18} />
            Settings
          </button>
        </div>
      </div>

      {/* ===== MAIN CONTENT ===== */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div
          className={`${
            theme === "dark" ? "bg-slate-900 border-slate-800" : "bg-slate-100 border-slate-200"
          } border-b p-4 flex items-center justify-between`}
        >
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-slate-800 rounded-lg transition"
            >
              {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
            </button>

            <select
              value={agentMode}
              onChange={(e) => setAgentMode(e.target.value)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold outline-none border ${
                theme === "dark"
                  ? "bg-slate-800 text-white border-slate-700"
                  : "bg-slate-200 text-slate-900 border-slate-300"
              }`}
            >
              <option value="chat">💬 Chat Mode</option>
              <option value="planner">🎯 Planner</option>
              <option value="executor">⚙️ Executor</option>
              <option value="analyzer">📊 Analyzer</option>
              <option value="critic">🔍 Critic</option>
            </select>

            <h2 className="text-lg font-semibold">{currentData.title}</h2>

            {/* Status Indicators */}
            <div className="flex items-center gap-2">
              {settings.enableMemory && (
                <div className="flex items-center gap-1 px-2 py-1 rounded bg-purple-600/20 text-purple-400 text-xs">
                  <BookOpen size={12} />
                  Memory
                </div>
              )}
              {settings.enableRAG && retrievedDocs.length > 0 && (
                <div className="flex items-center gap-1 px-2 py-1 rounded bg-green-600/20 text-green-400 text-xs">
                  <Layers size={12} />
                  RAG
                </div>
              )}
              {settings.enableReflection && (
                <div className="flex items-center gap-1 px-2 py-1 rounded bg-yellow-600/20 text-yellow-400 text-xs">
                  <Lightbulb size={12} />
                  Reflection
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {currentSession && messages.length > 0 && (
              <>
                <button
                  onClick={exportChat}
                  className="p-2 hover:bg-slate-800 rounded-lg transition"
                  title="Export"
                >
                  <Download size={20} />
                </button>
                <button
                  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  className="p-2 hover:bg-slate-800 rounded-lg transition"
                  title="Toggle theme"
                >
                  {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Messages Area */}
        <div
          className={`flex-1 overflow-y-auto p-6 space-y-4 ${
            theme === "dark" ? "bg-slate-950" : "bg-white"
          }`}
        >
          {!currentSession ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Brain className="w-20 h-20 mx-auto mb-4 text-blue-500 opacity-50" />
                <h1 className="text-3xl font-bold mb-2">AI Automation Studio</h1>
                <p className={`text-lg ${theme === "dark" ? "text-slate-400" : "text-slate-600"}`}>
                  Multi-Agent AI with Memory, RAG, Tools & Reflection
                </p>
                <p className={`text-sm mt-4 ${theme === "dark" ? "text-slate-500" : "text-slate-500"}`}>
                  💡 GenAI fact: Large language models can generate human-like text across 100+ languages.
                  <br />
                  🚀 GenAI fact: AI agents reduce complex planning time by 60% in real-world workflows.
                  <br />
                  🌱 GenAI fact: Context-aware memory and RAG improve response accuracy by over 40%.
                </p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Zap className="w-20 h-20 mx-auto mb-4 text-yellow-500 opacity-50" />
                <p className={`text-lg ${theme === "dark" ? "text-slate-400" : "text-slate-600"}`}>
                  Ready to process with {agentMode} mode
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? " justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-4xl rounded-2xl p-4 shadow-md ${
                    msg.role === "user"
                      ? theme === "dark"
                        ? "bg-blue-600"
                        : "bg-blue-500 text-white"
                      : theme === "dark"
                      ? "bg-slate-800"
                      : "bg-slate-100"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      {msg.role === "assistant" ? (
                        <Zap size={16} className="text-yellow-500" />
                      ) : (
                        <CheckCircle size={16} className="text-green-500" />
                      )}
                      <span className="text-xs font-semibold opacity-70">
                        {msg.role === "user"
                          ? "You"
                          : `AI (${msg.agentMode}) ${
                              msg.reflection ? "with reflection" : ""
                            }`}
                      </span>
                    </div>
                    <button
                      onClick={() => copyToClipboard(msg.content)}
                      className="opacity-0 hover:opacity-100 transition p-1 rounded hover:bg-slate-600"
                    >
                      <Copy size={14} />
                    </button>
                  </div>

                  {/* RAG Context */}
                  {msg.ragDocs && msg.ragDocs.length > 0 && (
                    <div className="mb-3 p-2 rounded text-xs bg-green-900/20 text-green-300 border border-green-700/30">
                      📚 Using {msg.ragDocs.length} document(s) from knowledge base
                    </div>
                  )}

                  <div className="prose max-w-none">
                    <ReactMarkdown
                      components={{
                        code({ node, inline, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || "");
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={oneDark}
                              language={match[1]}
                              {...props}
                            >
                              {String(children).replace(/\n$/, "")}
                            </SyntaxHighlighter>
                          ) : (
                            <code
                              className={`${
                                theme === "dark" ? "bg-slate-700" : "bg-slate-200"
                              } px-2 py-1 rounded text-sm`}
                              {...props}
                            >
                              {children}
                            </code>
                          );
                        },
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>

                  {/* Trace Viewer */}
                  {msg.role === "assistant" && msg.trace && msg.trace.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-700">
                      <button
                        onClick={() =>
                          setExpandedTraces((prev) => ({
                            ...prev,
                            [i]: !prev[i],
                          }))
                        }
                        className="flex items-center gap-2 text-sm font-semibold text-blue-400 hover:text-blue-300"
                      >
                        <Terminal size={16} />
                        Agent Trace ({msg.trace.length} steps)
                        <ChevronDown
                          size={16}
                          className={`transition ${
                            expandedTraces[i] ? "rotate-180" : ""
                          }`}
                        />
                      </button>

                      {expandedTraces[i] && (
                        <div className="mt-3 space-y-3">
                          {msg.trace.map((step, idx) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-lg border text-sm ${
                                theme === "dark"
                                  ? "bg-slate-900 border-slate-700"
                                  : "bg-slate-50 border-slate-300"
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-2">
                                <Terminal size={14} className="text-purple-500" />
                                <p className="font-semibold">{step.agent}</p>
                              </div>
                              <div className="text-xs space-y-1 opacity-70">
                                <p>
                                  <span className="font-semibold">Tool:</span>{" "}
                                  {step.tool_used || "none"}
                                </p>
                                <p>
                                  <span className="font-semibold">Input:</span>{" "}
                                  {JSON.stringify(step.input_data).substring(0, 60)}
                                </p>
                                <p>
                                  <span className="font-semibold">Output:</span>{" "}
                                  {JSON.stringify(step.output_data).substring(0, 60)}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Agent Reflection */}
                  {msg.role === "assistant" && msg.reflection && (
                    <div className="mt-4 pt-4 border-t border-yellow-700/30">
                      <div className="flex items-center gap-2 text-sm font-semibold text-yellow-400 mb-2">
                        <Lightbulb size={16} />
                        Agent Reflection
                      </div>
                      <p className="text-xs text-yellow-300/70">
                        {msg.reflection}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {loading && (
            <div className="flex justify-start">
              <div
                className={`${
                  theme === "dark" ? "bg-slate-800" : "bg-slate-100"
                } rounded-2xl p-4 shadow-md`}
              >
                <div className="flex items-center gap-2">
                  <div className="animate-spin">
                    <Zap className="text-yellow-500" size={20} />
                  </div>
                  <span className="text-sm font-semibold">
                    Multi-agent processing with RAG & memory...
                  </span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div
          className={`${
            theme === "dark" ? "bg-slate-900 border-slate-800" : "bg-slate-100 border-slate-200"
          } border-t p-6`}
        >
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendQuery();
                }
              }}
              placeholder="Describe your task with full context (memory + RAG enabled)..."
              className={`flex-1 p-4 rounded-lg outline-none resize-none ${
                theme === "dark"
                  ? "bg-slate-800 text-white border border-slate-700"
                  : "bg-white text-slate-900 border border-slate-300"
              }`}
              rows="3"
              disabled={!currentSession || loading}
            />

            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={!currentSession || loading}
              className="bg-slate-700 hover:bg-slate-600 text-white p-4 rounded-lg font-semibold flex items-center justify-center transition"
              title="Upload document for summary"
            >
              <FileText size={18} />
            </button>

            <button
              onClick={sendQuery}
              disabled={!currentSession || loading || !query.trim()}
              className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed p-4 rounded-lg font-semibold flex items-center justify-center transition"
            >
              <Send size={20} />
            </button>
          </div>

          <p className="text-xs text-slate-500 mt-2">
            ⌨️ Features: Memory • RAG • Tools • Reflection | Shift+Enter for new line
          </p>

          {/* Hidden file input - always in DOM */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleDocumentUpload}
            className="hidden"
            accept=".pdf,.txt,.docx,.md"
          />
        </div>
      </div>

      {/* ===== SETTINGS MODAL ===== */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div
            className={`${
              theme === "dark" ? "bg-slate-900" : "bg-white"
            } rounded-2xl p-8 max-w-3xl w-full shadow-2xl max-h-[90vh] overflow-y-auto`}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-3xl font-bold">⚙️ Advanced Settings</h2>
              <button
                onClick={() => setShowSettings(false)}
                className="p-2 hover:bg-slate-800 rounded-lg transition"
              >
                <X size={24} />
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Core Features */}
              <div
                className={`p-6 rounded-xl border ${
                  theme === "dark"
                    ? "bg-slate-800 border-slate-700"
                    : "bg-slate-50 border-slate-300"
                }`}
              >
                <h3 className="font-bold text-lg mb-4">Features</h3>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.enableMemory}
                      onChange={(e) =>
                        setSettings({ ...settings, enableMemory: e.target.checked })
                      }
                      className="w-4 h-4"
                    />
                    <span className="text-sm">
                      <BookOpen size={14} className="inline mr-1 text-purple-500" />
                      Long-term Memory
                    </span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.enableRAG}
                      onChange={(e) =>
                        setSettings({ ...settings, enableRAG: e.target.checked })
                      }
                      className="w-4 h-4"
                    />
                    <span className="text-sm">
                      <Layers size={14} className="inline mr-1 text-green-500" />
                      RAG System
                    </span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={settings.enableReflection}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          enableReflection: e.target.checked,
                        })
                      }
                      className="w-4 h-4"
                    />
                    <span className="text-sm">
                      <Lightbulb size={14} className="inline mr-1 text-yellow-500" />
                      Agent Reflection
                    </span>
                  </label>
                </div>
              </div>

              {/* AI Configuration */}
              <div
                className={`p-6 rounded-xl border ${
                  theme === "dark"
                    ? "bg-slate-800 border-slate-700"
                    : "bg-slate-50 border-slate-300"
                }`}
              >
                <h3 className="font-bold text-lg mb-4">AI Configuration</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold mb-2">
                      Temperature: {settings.temperature.toFixed(1)}
                    </label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={settings.temperature}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          temperature: parseFloat(e.target.value),
                        })
                      }
                      className="w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold mb-2">
                      Memory Retention: {settings.memoryRetention} items
                    </label>
                    <input
                      type="range"
                      min="10"
                      max="500"
                      step="10"
                      value={settings.memoryRetention}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          memoryRetention: parseInt(e.target.value),
                        })
                      }
                      className="w-full"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-6">
              <button className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 p-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition">
                <Save size={20} />
                Save Settings
              </button>
              <button
                onClick={() => setShowSettings(false)}
                className={`flex-1 p-3 rounded-lg font-semibold transition ${
                  theme === "dark"
                    ? "bg-slate-800 hover:bg-slate-700"
                    : "bg-slate-200 hover:bg-slate-300"
                }`}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}