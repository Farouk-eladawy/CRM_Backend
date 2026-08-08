import sys
import os

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_str = """                # Fetch System Rules & Schemas via Knowledge Engine
                knowledge_context = ""
                try:
                    import sys
                    import os
                    if "." not in sys.path:
                        sys.path.insert(0, ".")
                    from runtime.pi_brain.knowledge_engine import KnowledgeEngine
                    ke = KnowledgeEngine()
                    # We can pass the actor/user to get personal patterns if available
                    user_key = f"u_{str(actor.get('username') or 'internal').lower()}"
                    full_context = ke.get_full_context_for_pi(user_key=user_key, action_intent=prompt_payload.get("intent"))
                    knowledge_context = (
                        "=== SYSTEM KNOWLEDGE BASE ===\\n"
                        f"{full_context.get('system_rules', '')}\\n\\n"
                        "=== OPERATIONAL PATTERNS ===\\n"
                        f"{json.dumps(full_context.get('user_patterns', {}), ensure_ascii=False)}\\n\\n"
                        "=== ACTION SCHEMA (MANIFEST) ===\\n"
                        f"{json.dumps(full_context.get('required_schema', {}), ensure_ascii=False)}\\n"
                    )
                except Exception as e:
                    knowledge_context = f"Error loading KnowledgeEngine: {e}"

                return (
                    "You are PI, the external deep-reasoning analyzer for the FTS Travels internal operational assistant.\\n"
                    "You are analyzing an INTERNAL staff/admin case. You are not allowed to execute any action.\\n"
                    "You must return JSON only. No markdown, no explanation outside JSON.\\n\\n"
                    f"{knowledge_context}\\n\\n"
                    "Rules:\\n"
                    "- Respect the workflow contract: analysis only, never claim execution.\\n"
                    "- Distinguish confirmed facts from gaps or assumptions.\\n"
                    "- Keep the response in the same language style as the user context when generating reply text.\\n"
                    "- If the user asks you to add a watcher/monitor on a field (like Invoice Status), be aware that Airtable fields often use specific technical terms (e.g. 'succeeded' instead of 'Paid').\\n"
                    "- If you are not 100% sure about the exact value to watch for, DO NOT generate the action manifest. Instead, respond naturally asking the user what exact status they mean, and provide them with logical options to choose from.\\n"
                    "- If the case is still missing key data, prefer a clarifying question over guessing.\\n"
                    "- If the operation is sensitive, keep approval/local execution boundaries explicit.\\n\\n"
                    "Return exactly this JSON shape:\\n"
                    "{\\n"
                    "  \\"case_understanding\\": \\"short paragraph\\",\\n"
                    "  \\"confirmed_facts\\": [\\"...\\"],\\n"
                    "  \\"missing_information\\": [\\"...\\"],\\n"
                    "  \\"risk_flags\\": [\\"...\\"],\\n"
                    "  \\"recommended_internal_reply\\": \\"message to send back to the internal user\\",\\n"
                    "  \\"recommended_next_step\\": \\"short operational next step\\",\\n"
                    "  \\"should_ask_clarifying_question\\": true,\\n"
                    "  \\"clarifying_question\\": \\"...\\",\\n"
                    "  \\"approval_required\\": true,\\n"
                    "  \\"execution_guidance\\": \\"no_execution|approval_gate|local_executor_only|ask_user\\",\\n"
                    "  \\"confidence\\": 0.0,\\n"
                    "  \\"action_manifest\\": [\\n"
                    "    {\\n"
                    "      \\"type\\": \\"create_invoice\\",\\n"
                    "      \\"target_record\\": \\"rec...\\",\\n"
                    "      \\"requires_approval\\": true,\\n"
                    "      \\"payload\\": {}\\n"
                    "    }\\n"
                    "  ]\\n"
                    "}\\n\\n"
                    f"Delegation payload:\\n{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
                )"""

new_str = """                # Fetch System Rules & Schemas via Knowledge Engine
                knowledge_context = ""
                try:
                    import sys
                    import os
                    if "." not in sys.path:
                        sys.path.insert(0, ".")
                    from runtime.pi_brain.knowledge_engine import KnowledgeEngine
                    ke = KnowledgeEngine()
                    # We can pass the actor/user to get personal patterns if available
                    user_key = f"u_{str(actor.get('username') or 'internal').lower()}"
                    full_context = ke.get_full_context_for_pi(user_key=user_key, action_intent=prompt_payload.get("intent"))
                    
                    schemas_str = ""
                    if prompt_payload.get("intent") == "agentic_orchestrator":
                        schemas_str = (
                            "=== ALL AVAILABLE ACTION SCHEMAS ===\\n"
                            "You can choose ONE or MORE of the following schemas to build your 'action_manifest' if you decide to take an action.\\n"
                            f"{json.dumps(full_context.get('all_available_schemas', {}), ensure_ascii=False)}\\n"
                        )
                    else:
                        schemas_str = (
                            "=== ACTION SCHEMA (MANIFEST) ===\\n"
                            f"{json.dumps(full_context.get('required_schema', {}), ensure_ascii=False)}\\n"
                        )

                    knowledge_context = (
                        "=== SYSTEM KNOWLEDGE BASE ===\\n"
                        f"{full_context.get('system_rules', '')}\\n\\n"
                        "=== OPERATIONAL PATTERNS ===\\n"
                        f"{json.dumps(full_context.get('user_patterns', {}), ensure_ascii=False)}\\n\\n"
                        f"{schemas_str}"
                    )
                except Exception as e:
                    knowledge_context = f"Error loading KnowledgeEngine: {e}"

                return (
                    "You are PI, the external deep-reasoning analyzer and Agentic OS for the FTS Travels internal system.\\n"
                    "You are acting as an autonomous orchestrator. You understand the user's request and map it to available system capabilities.\\n"
                    "You must return JSON only. No markdown, no explanation outside JSON.\\n\\n"
                    f"{knowledge_context}\\n\\n"
                    "Rules:\\n"
                    "- Respect the workflow contract: analysis and delegation.\\n"
                    "- Distinguish confirmed facts from gaps or assumptions.\\n"
                    "- Keep the response in the same language style as the user context when generating reply text.\\n"
                    "- If the user wants to execute an action (like creating an invoice, adding a watcher, etc.), look at ALL AVAILABLE ACTION SCHEMAS and output the exact JSON structure in 'action_manifest'.\\n"
                    "- If you are not 100% sure about the exact value to watch for, DO NOT generate the action manifest. Instead, respond naturally asking the user what exact status they mean, and provide them with logical options to choose from.\\n"
                    "- If the case is still missing key data, prefer a clarifying question over guessing.\\n"
                    "- If the operation is sensitive, keep approval/local execution boundaries explicit.\\n\\n"
                    "Return exactly this JSON shape:\\n"
                    "{\\n"
                    "  \\"case_understanding\\": \\"short paragraph\\",\\n"
                    "  \\"confirmed_facts\\": [\\"...\\"],\\n"
                    "  \\"missing_information\\": [\\"...\\"],\\n"
                    "  \\"risk_flags\\": [\\"...\\"],\\n"
                    "  \\"recommended_internal_reply\\": \\"message to send back to the internal user\\",\\n"
                    "  \\"recommended_next_step\\": \\"short operational next step\\",\\n"
                    "  \\"should_ask_clarifying_question\\": true,\\n"
                    "  \\"clarifying_question\\": \\"...\\",\\n"
                    "  \\"approval_required\\": true,\\n"
                    "  \\"execution_guidance\\": \\"no_execution|approval_gate|local_executor_only|ask_user\\",\\n"
                    "  \\"confidence\\": 0.0,\\n"
                    "  \\"action_manifest\\": [\\n"
                    "    {\\n"
                    "      \\"type\\": \\"create_invoice\\",\\n"
                    "      \\"target_record\\": \\"rec...\\",\\n"
                    "      \\"requires_approval\\": true,\\n"
                    "      \\"payload\\": {}\\n"
                    "    }\\n"
                    "  ]\\n"
                    "}\\n\\n"
                    f"Delegation payload:\\n{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
                )"""

if old_str in content:
    content = content.replace(old_str, new_str)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Prompt updated successfully.")
else:
    print("old_str not found in content!")
