import { useEffect, useState } from "react";
import { api } from "../api";
import type { Account, LinkableAccount } from "../types";

export function SyncPage({ accounts }: { accounts: Account[] }) {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [setupToken, setSetupToken] = useState("");
  const [linkable, setLinkable] = useState<LinkableAccount[]>([]);
  const [chosenAccount, setChosenAccount] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const loadStatus = () => {
    api.syncStatus().then((s) => setConnected(s.connected)).catch((e) => setError(String(e)));
  };

  const loadLinkable = () => {
    api.syncLinkableAccounts().then(setLinkable).catch((e) => setError(String(e)));
  };

  useEffect(loadStatus, []);
  useEffect(() => {
    if (connected) loadLinkable();
  }, [connected]);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.syncConnect(setupToken.trim());
      setSetupToken("");
      loadStatus();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  const handleLink = async (remote: LinkableAccount) => {
    const accountId = chosenAccount[remote.simplefin_account_id];
    if (!accountId) return;
    try {
      await api.syncLinkAccount(remote.simplefin_account_id, Number(accountId), remote.org);
      loadLinkable();
    } catch (err) {
      setError(String(err));
    }
  };

  const handleSync = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await api.syncRun();
      setLastResult(
        `Synced ${result.accounts_synced} account(s): ${result.transactions_imported} new, ` +
          `${result.transactions_matched} matched to existing entries.`
      );
      loadLinkable();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  };

  if (connected === null) return <p>Loading…</p>;

  return (
    <div>
      <h2>Bank Sync</h2>
      {error && <p className="error">{error}</p>}

      {!connected ? (
        <div className="category-group">
          <p>
            Connect to SimpleFIN Bridge with a setup token (from your SimpleFIN Bridge account, after
            you've linked your banks there). Setup tokens are single-use.
          </p>
          <form onSubmit={handleConnect} className="inline-form">
            <input
              placeholder="Paste setup token…"
              value={setupToken}
              onChange={(e) => setSetupToken(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="submit" disabled={busy || !setupToken.trim()}>
              Connect
            </button>
          </form>
        </div>
      ) : (
        <>
          <div className="category-group">
            <h3>Link accounts</h3>
            <table>
              <thead>
                <tr>
                  <th>Institution</th>
                  <th>SimpleFIN account</th>
                  <th>Balance</th>
                  <th>Linked to</th>
                </tr>
              </thead>
              <tbody>
                {linkable.map((remote) => (
                  <tr key={remote.simplefin_account_id}>
                    <td>{remote.org ?? "—"}</td>
                    <td>{remote.name}</td>
                    <td>{remote.balance ?? "—"}</td>
                    <td>
                      {remote.linked_account_id ? (
                        accounts.find((a) => a.id === remote.linked_account_id)?.name ?? "Linked"
                      ) : (
                        <span className="inline-form">
                          <select
                            value={chosenAccount[remote.simplefin_account_id] ?? ""}
                            onChange={(e) =>
                              setChosenAccount({ ...chosenAccount, [remote.simplefin_account_id]: e.target.value })
                            }
                          >
                            <option value="">Choose local account…</option>
                            {accounts.map((a) => (
                              <option key={a.id} value={a.id}>
                                {a.name}
                              </option>
                            ))}
                          </select>
                          <button onClick={() => handleLink(remote)}>Link</button>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
                {linkable.length === 0 && (
                  <tr>
                    <td colSpan={4} className="empty">
                      No accounts found at SimpleFIN
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <button onClick={handleSync} disabled={busy}>
            {busy ? "Syncing…" : "Sync now"}
          </button>
          {lastResult && <p>{lastResult}</p>}
        </>
      )}
    </div>
  );
}
