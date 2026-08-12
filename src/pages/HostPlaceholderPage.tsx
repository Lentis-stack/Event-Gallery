import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Host placeholder — now redirects to the real host console.
 * Kept so any old links to /host/placeholder still work.
 */
export default function HostPlaceholderPage() {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/host/console', { replace: true });
  }, [navigate]);

  return null;
}
