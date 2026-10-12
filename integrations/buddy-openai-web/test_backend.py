import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch, MagicMock
s=importlib.util.spec_from_file_location('backend',Path(__file__).with_name('__init__.py'))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def test_requires_completed_search(self):
  with self.assertRaises(RuntimeError): m.collect([N(type='response.completed')])
 def test_failed_response_rejected(self):
  with self.assertRaises(RuntimeError): m.collect([N(type='response.failed')])
 def test_citations_and_search(self):
  events=[N(type='response.output_item.done',item=N(type='web_search_call',status='completed',action={'type':'search','sources':[]})),N(type='response.output_text.delta',delta='answer'),N(type='response.output_item.done',item=N(type='message',content=[N(annotations=[N(type='url_citation',url='https://example.com',title='Example')])])),N(type='response.completed')]
  text,sources,actions=m.collect(events)
  self.assertEqual(text,'answer');self.assertEqual(sources,{'https://example.com':'Example'})
 def test_extract_rejects_unopened_page(self):
  p=m.OpenAIWeb();p._run=lambda _:('invented',{},[{'type':'search'}])
  self.assertIn('error',p.extract(['https://example.com'])[0])
 def test_extract_labels_summary(self):
  p=m.OpenAIWeb();p._run=lambda _:('summary',{},[{'type':'open_page','url':'https://example.com'}])
  r=p.extract(['https://example.com'])[0]
  self.assertEqual(r['metadata']['content_type'],'model_summary')
 def test_search_error_redacts_secrets(self):
  p=m.OpenAIWeb()
  def fail(_): raise ValueError('secret must not appear')
  p._run=fail;r=p.search('query')
  self.assertFalse(r['success']);self.assertNotIn('secret',r['error'])
 def test_primary_success_never_bills_api(self):
  p=m.OpenAIWeb();p._request=MagicMock(return_value=('ok',{},[]))
  self.assertEqual(p._run('q')[0],'ok')
  p._request.assert_called_once_with('q','openai-codex')
 def test_rate_limit_uses_api_and_cooldown(self):
  p=m.OpenAIWeb();p._request=MagicMock(side_effect=[RuntimeError('429'),('api',{},[]),('api2',{},[])])
  with patch.object(m.time,'monotonic',return_value=100):
   self.assertEqual(p._run('q')[0],'api')
   self.assertEqual(p._run('q2')[0],'api2')
  self.assertEqual([c.args[1] for c in p._request.call_args_list],['openai-codex','openai-api','openai-api'])
 def test_primary_recovers_after_cooldown(self):
  p=m.OpenAIWeb();p._request=MagicMock(side_effect=[RuntimeError('401'),('api',{},[]),('codex',{},[])])
  with patch.object(m.time,'monotonic',return_value=100): p._run('q')
  with patch.object(m.time,'monotonic',return_value=161): self.assertEqual(p._run('q')[0],'codex')
  self.assertEqual(p._failures,0)
  self.assertEqual(p._retry_at,0)
 def test_both_routes_fail_without_leaking_errors(self):
  p=m.OpenAIWeb();p._request=MagicMock(side_effect=RuntimeError('private-token'))
  r=p.search('q');self.assertFalse(r['success']);self.assertNotIn('private-token',r['error'])
  self.assertEqual(p._request.call_count,2)
 def test_extract_falls_back_and_still_requires_exact_page(self):
  p=m.OpenAIWeb();p._request=MagicMock(side_effect=[RuntimeError('quota'),('summary',{},[{'type':'open_page','url':'https://example.com'}])])
  self.assertEqual(p.extract(['https://example.com'])[0]['metadata']['content_type'],'model_summary')
 def test_api_uses_existing_scoped_key_and_pinned_endpoint(self):
  p=m.OpenAIWeb()
  with patch('agent.secret_scope.get_secret',return_value='test-key') as key, patch('openai.OpenAI') as client, patch.object(m,'collect',return_value=('ok',{},[])):
   p._request('q','openai-api')
   key.assert_any_call('OPENAI_API_KEY')
   self.assertEqual(client.call_args.kwargs['api_key'],'test-key')
   self.assertEqual(client.call_args.kwargs['base_url'],'https://api.openai.com/v1')
 def test_missing_api_key_never_calls_network(self):
  with patch('agent.secret_scope.get_secret',return_value=''), patch('openai.OpenAI') as client:
   with self.assertRaises(RuntimeError): m.OpenAIWeb()._request('q','openai-api')
   client.assert_not_called()
 def test_wrong_subscription_endpoint_rejected(self):
  with patch('hermes_cli.runtime_provider.resolve_runtime_provider',return_value={'provider':'openai-codex','base_url':'https://example.com','api_key':'test'}), patch('openai.OpenAI') as client:
   with self.assertRaises(RuntimeError): m.OpenAIWeb()._request('q','openai-codex')
   client.assert_not_called()
if __name__=='__main__': unittest.main()
