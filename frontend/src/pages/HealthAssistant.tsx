import React, { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  Bot,
  User,
  Send,
  Plus,
  ShieldAlert,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { format } from "date-fns";

interface ChatMessage {
  id?: string;
  sender: "user" | "assistant";
  content: string;
  created_at?: string;
}

interface ChatConversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

const SUGGESTED_PROMPTS = [
  "What are my latest readings?",
  "Show my recent heart-rate trend",
  "What factors contributed to the current risk signal?",
  "What changed compared with my baseline?",
  "How do I understand CarePulse vital sign alerts?",
  "How can I maintain a healthy lifestyle?",
];

export const HealthAssistant: React.FC = () => {
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [emergencyWarning, setEmergencyWarning] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const queryClient = useQueryClient();
  const { status: socketStatus } = useMonitoringSocket();

  // Fetch list of conversations
  const { data: conversations, refetch: refetchConversations } = useQuery({
    queryKey: ["chat-conversations"],
    queryFn: () => api.get<ChatConversation[]>("/api/v1/chat/conversations"),
  });

  // Fetch active conversation detail
  const { data: activeConv } = useQuery({
    queryKey: ["chat-conversation", activeConversationId],
    queryFn: () => api.get<ChatConversation>(`/api/v1/chat/conversations/${activeConversationId}`),
    enabled: !!activeConversationId,
  });

  useEffect(() => {
    if (activeConv?.messages) {
      setLocalMessages(activeConv.messages);
    }
  }, [activeConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [localMessages]);

  // Send message mutation
  const sendMutation = useMutation({
    mutationFn: (message: string) =>
      api.post<{ response: string; timestamp: string; conversation_id: string; emergency_warning: boolean }>(
        "/api/v1/chat",
        {
          message,
          conversation_id: activeConversationId || undefined,
        }
      ),
    onSuccess: (data) => {
      setActiveConversationId(data.conversation_id);
      setEmergencyWarning(data.emergency_warning);

      // Add assistant response to local messages
      const assistantMsg: ChatMessage = {
        sender: "assistant",
        content: data.response,
        created_at: data.timestamp,
      };
      setLocalMessages((prev) => [...prev, assistantMsg]);

      queryClient.invalidateQueries({ queryKey: ["chat-conversations"] });
      queryClient.invalidateQueries({ queryKey: ["chat-conversation", data.conversation_id] });
    },
    onError: (err: any) => {
      const errorMsg: ChatMessage = {
        sender: "assistant",
        content: `⚠️ Error: ${err?.message || "Failed to process request. Please try again."}\n\n*CarePulse Health Assistant provides general health information and does not replace professional medical advice.*`,
      };
      setLocalMessages((prev) => [...prev, errorMsg]);
    },
  });

  const handleSend = (textToSend?: string) => {
    const text = textToSend || inputMessage;
    if (!text.trim() || sendMutation.isPending) return;

    const userMsg: ChatMessage = {
      sender: "user",
      content: text,
      created_at: new Date().toISOString(),
    };

    setLocalMessages((prev) => [...prev, userMsg]);
    setInputMessage("");
    setEmergencyWarning(false);
    sendMutation.mutate(text);
  };

  const startNewChat = () => {
    setActiveConversationId(null);
    setLocalMessages([]);
    setEmergencyWarning(false);
    setInputMessage("");
  };

  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.delete(`/api/v1/chat/conversations/${convId}`);
      if (activeConversationId === convId) {
        startNewChat();
      }
      refetchConversations();
    } catch {}
  };

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-12rem)] min-h-[600px]">
        {/* Left Sidebar: Conversations & Actions */}
        <div className="w-full lg:w-72 bg-gray-900 border border-gray-800 rounded-2xl p-4 flex flex-col justify-between shrink-0">
          <div>
            <button
              onClick={startNewChat}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-xs flex items-center justify-center gap-2 transition-colors shadow-lg shadow-blue-600/20 mb-4"
            >
              <Plus className="w-4 h-4" /> New Health Chat
            </button>

            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 px-2">
              Recent Conversations
            </div>

            <div className="space-y-1 max-h-[350px] overflow-y-auto pr-1">
              {conversations && conversations.length > 0 ? (
                conversations.map((conv) => {
                  const isActive = conv.id === activeConversationId;
                  return (
                    <div
                      key={conv.id}
                      onClick={() => setActiveConversationId(conv.id)}
                      className={`w-full p-2.5 rounded-xl text-xs text-left flex items-center justify-between cursor-pointer transition-colors ${
                        isActive
                          ? "bg-blue-600/20 text-blue-300 border border-blue-500/30"
                          : "text-gray-300 hover:bg-gray-800/60"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate pr-2">
                        <MessageSquare className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                        <span className="truncate">{conv.title}</span>
                      </div>
                      <button
                        onClick={(e) => deleteConversation(conv.id, e)}
                        className="text-gray-500 hover:text-red-400 p-1"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })
              ) : (
                <div className="text-[11px] text-gray-500 text-center py-4 italic">
                  No previous chats yet
                </div>
              )}
            </div>
          </div>

          <div className="p-3 bg-gray-950 rounded-xl border border-gray-800/80 text-[11px] text-gray-400 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold text-amber-400">
              <ShieldAlert className="w-3.5 h-3.5 shrink-0" /> Safety Notice
            </div>
            <p>De-identifies inputs. Does not diagnose illness or replace professional care.</p>
          </div>
        </div>

        {/* Main Chat Interface */}
        <div className="flex-1 bg-gray-900 border border-gray-800 rounded-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-4 bg-gray-900/90 border-b border-gray-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600/20 text-blue-400 rounded-xl border border-blue-500/30">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-100 flex items-center gap-2">
                  Health Assistant
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                    AI EDUCATIONAL
                  </span>
                </h2>
                <p className="text-xs text-gray-400">General health education &amp; CarePulse alert guidance</p>
              </div>
            </div>

            <button
              onClick={startNewChat}
              className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700"
            >
              <RefreshCw className="w-3 h-3" /> Reset Chat
            </button>
          </div>

          {/* Mandatory Disclaimer Banner */}
          <div className="bg-blue-950/40 border-b border-blue-800/40 px-4 py-2 text-center text-xs text-blue-300 font-medium flex items-center justify-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <span>
              CarePulse Health Assistant provides general health information and does not replace professional medical advice.
            </span>
          </div>

          {/* Emergency Red Warning Banner */}
          {emergencyWarning && (
            <div className="bg-red-950 border-b border-red-800 px-4 py-3 text-xs text-red-200 font-semibold flex items-center justify-center gap-2 animate-pulse">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
              <span>EMERGENCY ALERT: Potential urgent medical symptoms detected. Seek emergency professional care immediately.</span>
            </div>
          )}

          {/* Messages Scroll Area */}
          <div className="flex-1 p-4 lg:p-6 overflow-y-auto space-y-4">
            {localMessages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 max-w-lg mx-auto">
                <div className="p-4 bg-blue-600/10 text-blue-400 rounded-2xl mb-4 border border-blue-500/20">
                  <Bot className="w-10 h-10" />
                </div>
                <h3 className="text-lg font-bold text-gray-200 mb-1">How can I assist your health today?</h3>
                <p className="text-xs text-gray-400 mb-6">
                  Ask general questions about lifestyle, sleep, nutrition, hydration, doctor visit preparation, or understanding CarePulse alerts.
                </p>

                <div className="w-full space-y-2 text-left">
                  <div className="text-xs font-semibold text-gray-400 mb-2">Suggested Questions:</div>
                  {SUGGESTED_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(prompt)}
                      className="w-full text-left p-3 bg-gray-950 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-xl text-xs text-gray-300 transition-colors flex items-center justify-between"
                    >
                      <span>{prompt}</span>
                      <Sparkles className="w-3.5 h-3.5 text-blue-400 opacity-60" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              localMessages.map((msg, idx) => {
                const isUser = msg.sender === "user";
                return (
                  <div
                    key={idx}
                    className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                  >
                    <div
                      className={`p-2 rounded-xl shrink-0 ${
                        isUser
                          ? "bg-blue-600 text-white"
                          : "bg-gray-800 text-blue-400 border border-gray-700"
                      }`}
                    >
                      {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    <div
                      className={`max-w-[80%] rounded-2xl p-4 text-xs leading-relaxed space-y-2 ${
                        isUser
                          ? "bg-blue-600 text-white rounded-tr-none"
                          : "bg-gray-950 border border-gray-800 text-gray-200 rounded-tl-none"
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                      {msg.created_at && (
                        <div
                          className={`text-[10px] text-right font-mono ${
                            isUser ? "text-blue-200" : "text-gray-500"
                          }`}
                        >
                          {format(new Date(msg.created_at), "HH:mm")}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {sendMutation.isPending && (
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-xl bg-gray-800 text-blue-400 border border-gray-700">
                  <Bot className="w-4 h-4 animate-bounce" />
                </div>
                <div className="bg-gray-950 border border-gray-800 text-gray-400 rounded-2xl p-4 text-xs flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
                  <span>Generating health assistant guidance...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <div className="p-4 bg-gray-900 border-t border-gray-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask a health question (e.g. nutrition, sleep, doctor prep)..."
                disabled={sendMutation.isPending}
                className="flex-1 bg-gray-950 border border-gray-700 focus:border-blue-500 rounded-xl px-4 py-3 text-xs text-gray-100 focus:outline-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || sendMutation.isPending}
                className="p-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition-colors disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
