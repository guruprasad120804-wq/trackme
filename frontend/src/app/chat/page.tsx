"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Bot,
  User,
  Plus,
  MessageCircle,
  Trash2,
  Sparkles,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  sendChatMessage,
  getConversations,
  getConversationMessages,
  deleteConversation,
} from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

const SUGGESTIONS = [
  "What's my portfolio worth today?",
  "Show me my top performing investments",
  "Am I well diversified?",
  "What's my XIRR across all funds?",
  "Suggest how to rebalance my portfolio",
];

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [activeConvo, setActiveConvo] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const queryClient = useQueryClient();

  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => getConversations().then((r) => r.data),
  });

  const { data: convoMessages } = useQuery({
    queryKey: ["conversation-messages", activeConvo],
    queryFn: () =>
      activeConvo
        ? getConversationMessages(activeConvo).then((r) => r.data)
        : Promise.resolve([]),
    enabled: !!activeConvo,
  });

  useEffect(() => {
    if (convoMessages) setMessages(convoMessages);
  }, [convoMessages]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isTyping]);

  const mutation = useMutation({
    mutationFn: (message: string) =>
      sendChatMessage(message, activeConvo || undefined).then((r) => r.data),
    onMutate: (message) => {
      setMessages((prev) => [
        ...prev,
        { id: `temp-${Date.now()}`, role: "user", content: message, created_at: new Date().toISOString() },
      ]);
      setIsTyping(true);
      setInput("");
    },
    onSuccess: (data) => {
      setIsTyping(false);
      if (!activeConvo) setActiveConvo(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        { id: `ai-${Date.now()}`, role: "assistant", content: data.message, created_at: new Date().toISOString() },
      ]);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: () => {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        { id: `err-${Date.now()}`, role: "assistant", content: "Sorry, something went wrong. Please try again.", created_at: new Date().toISOString() },
      ]);
    },
  });

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || mutation.isPending) return;
    mutation.mutate(msg);
  };

  const handleNewChat = () => {
    setActiveConvo(null);
    setMessages([]);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen">
      {/* Conversation sidebar */}
      <div className="w-72 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <Button
            onClick={handleNewChat}
            className="w-full bg-amber hover:bg-amber-dark text-navy font-semibold"
            size="sm"
          >
            <Plus className="h-4 w-4 mr-2" />
            New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {(conversations || []).map((c: any) => (
            <button
              key={c.id}
              onClick={() => setActiveConvo(c.id)}
              className={cn(
                "w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors group",
                activeConvo === c.id
                  ? "bg-amber/15 text-amber"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <div className="flex items-center justify-between">
                <span className="truncate flex-1">{c.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteConversation(c.id);
                    queryClient.invalidateQueries({ queryKey: ["conversations"] });
                    if (activeConvo === c.id) handleNewChat();
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-all"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
              <span className="text-[10px] text-muted-foreground">{c.message_count} messages</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        <Header title="AI Assistant" subtitle="Ask anything about your portfolio" />

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-amber/10 mb-4">
                <Sparkles className="h-8 w-8 text-amber" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">TrackMe AI</h3>
              <p className="text-sm text-muted-foreground max-w-md mb-8">
                Ask me anything about your portfolio, investments, or financial concepts.
              </p>
              <div className="flex flex-wrap gap-2 max-w-lg justify-center">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => {
                      setInput(s);
                      inputRef.current?.focus();
                    }}
                    className="px-3 py-2 text-xs font-medium bg-secondary border border-border rounded-lg text-muted-foreground hover:text-foreground hover:border-amber/30 transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex gap-3",
                  msg.role === "user" ? "justify-end" : "justify-start"
                )}
              >
                {msg.role === "assistant" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber/10">
                    <Bot className="h-4 w-4 text-amber" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-2xl rounded-xl px-4 py-3 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "bg-amber text-navy font-medium"
                      : "bg-secondary text-foreground"
                  )}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                </div>
                {msg.role === "user" && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary">
                    <User className="h-4 w-4 text-muted-foreground" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3"
            >
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber/10">
                <Bot className="h-4 w-4 text-amber" />
              </div>
              <div className="bg-secondary rounded-xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:0ms]" />
                  <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:150ms]" />
                  <span className="h-2 w-2 rounded-full bg-muted-foreground animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border p-4">
          <div className="flex items-end gap-3 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your portfolio..."
                rows={1}
                className="w-full resize-none rounded-xl border border-border bg-secondary px-4 py-3 pr-12 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-amber/50 focus:border-amber"
              />
            </div>
            <Button
              onClick={handleSend}
              disabled={!input.trim() || mutation.isPending}
              size="icon"
              className="h-11 w-11 rounded-xl bg-amber hover:bg-amber-dark text-navy shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-center text-[10px] text-muted-foreground mt-2">
            AI may make mistakes. Not financial advice.
          </p>
        </div>
      </div>
    </div>
  );
}
