import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
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
 def test_search_does_not_fallback(self):
  p=m.OpenAIWeb()
  def fail(_): raise ValueError('secret must not appear')
  p._run=fail;r=p.search('query')
  self.assertFalse(r['success']);self.assertNotIn('secret',r['error'])
if __name__=='__main__': unittest.main()
