import { useEffect, useState } from "react";
import { api } from "./api";
import { currentMonthStr } from "./money";
import { AccountsPage } from "./pages/AccountsPage";
import { BudgetPage } from "./pages/BudgetPage";
import { RegisterPage } from "./pages/RegisterPage";
import type { Account } from "./types";

type Tab = "budget" | "accounts" | "register";

export default function App() {
  const [tab, setTab] = useState<Tab>("budget");
  const [month, setMonth] = useState(currentMonthStr());
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<number | null>(null);

  useEffect(() => {
    api.listAccounts().then(setAccounts).catch(() => {});
  }, [tab, selectedAccount]);

  return (
    <div className="app">
      <header>
        <h1>Budget Birdie</h1>
        <nav>
          <button className={tab === "budget" ? "active" : ""} onClick={() => setTab("budget")}>
            Budget
          </button>
          <button className={tab === "accounts" ? "active" : ""} onClick={() => setTab("accounts")}>
            Accounts
          </button>
        </nav>
      </header>

      <main>
        {tab === "budget" && <BudgetPage month={month} setMonth={setMonth} />}
        {tab === "accounts" && !selectedAccount && (
          <AccountsPage
            onSelect={(id) => {
              setSelectedAccount(id);
              setTab("register");
            }}
          />
        )}
        {tab === "register" && selectedAccount && (
          <div>
            <button
              className="back-link"
              onClick={() => {
                setSelectedAccount(null);
                setTab("accounts");
              }}
            >
              ← Accounts
            </button>
            <RegisterPage accountId={selectedAccount} accounts={accounts} />
          </div>
        )}
      </main>
    </div>
  );
}
