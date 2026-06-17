import asyncio
import subprocess
import time
import os
from pathlib import Path
from playwright.async_api import async_playwright
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# Configurações de ambiente para silenciar avisos do Node
os.environ["NODE_OPTIONS"] = "--no-deprecation"

class ScraperCrawl4AI:
    def __init__(self):
        # Seletores para remover elementos indesejados (exatamente como no filtro original)
        self.excluded_selector = (
            ".toc, .wds-global-footer, #catlinks, .printfooter, .global-top-navigation, "
            ".notifications-placeholder, #community-navigation, .community-header-wrapper, "
            ".global-explore-navigation, .global-footer, .global-footer__content, "
            ".global-footer__bottom, .fandom-community-header, #navigator, #header, "
            ".full_hr, .menubar, #toolbar, #lastmodified, #footer, #cosmos-footer, "
            "#cosmos-toolbar, .cosmos-header, #cosmos-banner, .mw-header, #mw-head, "
            "#mw-panel, #mw-page-base, #mw-head-base, .mw-footer, .mw-footer-container, "
            ".vector-column-end, .vector-sticky-pinned-container, .azltable, .page__right-rail, "
            "#google_translate_element, #onetrust-banner-sdk, #onetrust-consent-sdk, "
            "#top_leaderboard-odyssey-wrapper, .mw-cookiewarning-container, .nv-view, .nv-talk, "
            ".nv-edit, .navibox, .pcomment, #google_translate_element, #goog-gt-tt, "
            "#goog-gt-vt, .adthrive-comscore, .adthrive-footer-message, .adthrive-ad, "
            ".adthrive-footer, .raptive-content-terms-modal, .adthrive-ccpa-modal, "
            "#adt-ii, #adthrive-mcmp"
        )
        # Tenta carregar configuração se disponível
        try:
            import config_manager
            self.config = config_manager.load_config()
        except ImportError:
            self.config = {}
            
        self.browser_path = self._get_browser_path()

    def _get_browser_path(self):
        """Tenta encontrar um navegador compatível no sistema."""
        # 1. Tenta o caminho manual do config.json
        manual_path = self.config.get("browser_config", {}).get("binary_path")
        if manual_path and os.path.exists(manual_path):
            return manual_path

        # 2. Caminhos comuns para Brave, Chrome e Edge (Windows prioritário)
        potential_paths = [
            # Brave
            os.path.expandvars(r"%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            os.path.expandvars(r"%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            # Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            # Edge
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        ]

        for path in potential_paths:
            if os.path.exists(path):
                print(f"✅ Navegador encontrado: {path}")
                return path

        # Se nada for encontrado, retorna o padrão antigo como fallback e avisa
        print("⚠️ Nenhum navegador compatível encontrado automaticamente.")
        return r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

    async def _start_browser(self):
        """Inicia o navegador em uma instância isolada com porta de debug habilitada."""
        print(f"🌐 Iniciando nova instância isolada do navegador em: {self.browser_path}")
        
        # Cria um diretório de perfil local para garantir que seja uma janela nova e isolada
        profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".crawl4ai_profile")
        os.makedirs(profile_path, exist_ok=True)
        
        # Comando para abrir o navegador via subprocess
        cmd = [
            self.browser_path,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile_path}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1280,720"
        ]
        
        proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("⏳ Aguardando inicialização do ambiente isolado...")
        await asyncio.sleep(5)  # Aguarda o navegador estabilizar (ASYNC)
        return proc

    async def scrape(self, urls):
        """
        Executa o processo de scraping:
        1. Abre o Navegador
        2. Resolve o Cloudflare (se houver) para cada URL
        3. Captura o HTML de cada página
        4. Processa com Crawl4AI via prefixo raw://
        """
        if isinstance(urls, str):
            urls = [urls]

        # Limpa URLs vazias ou duplicadas
        urls = [u.strip() for u in urls if u and u.strip()]
        if not urls:
            return ""

        browser_proc = await self._start_browser()
        all_markdowns = []
        
        async with async_playwright() as p:
            try:
                # Conecta ao navegador via IPv4 para evitar erro ECONNREFUSED ::1
                browser = None
                for i in range(10): # Aumentado o número de tentativas
                    try:
                        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=30000)
                        break
                    except Exception as e:
                        if i == 9: raise e
                        print(f"   ⏳ Tentativa {i+1} de conexão falhou, tentando novamente...")
                        await asyncio.sleep(2)

                if not browser:
                    raise Exception("Não foi possível conectar ao navegador via CDP.")

                # Pega o contexto padrão
                context = browser.contexts[0]
                
                # REUTILIZA UMA ÚNICA PÁGINA para evitar erros de "Target closed" e "Failed to open tab"
                page = await context.new_page()
                
                # Fecha as abas iniciais vazias (exceto a nossa)
                for p_to_close in context.pages:
                    if p_to_close != page:
                        try:
                            await p_to_close.close()
                        except: pass

                # Inicializa o crawler SEM configuração de browser para evitar conflitos de Playwright
                # Se usarmos raw://, o Crawl4AI pode funcionar apenas como processador de HTML
                async with AsyncWebCrawler(verbose=False) as crawler:
                    for url in urls:
                        try:
                            # Verifica se o browser ainda está conectado
                            if not browser.is_connected():
                                print("⚠️ Conexão com o navegador perdida. Tentando reconectar...")
                                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=30000)
                                context = browser.contexts[0]
                                page = await context.new_page()

                            print(f"📥 Acessando: {url}")
                            await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                            
                            # Loop de detecção do Cloudflare (Ray ID)
                            print(f"🔍 Verificando proteções para {url}...")
                            for attempt in range(300): # 5 minutos
                                try:
                                    status = await page.evaluate("""() => {
                                        const isWaiting = document.title.includes('Just a moment') || 
                                                         document.body.innerText.includes('Checking your browser') ||
                                                         document.body.innerText.includes('verify you are human') ||
                                                         !!document.querySelector('#challenge-form') ||
                                                         !!document.querySelector('.cf-browser-verification');
                                        
                                        const hasRayId = !!(document.querySelector('[id*="ray-id"]') || 
                                                          document.querySelector('[class*="ray-id"]') || 
                                                          document.body.innerText.includes('Ray ID'));
                                        
                                        return { isBlocked: hasRayId || isWaiting };
                                    }""")
                                    
                                    if not status['isBlocked']:
                                        # Verifica se o conteúdo real carregou
                                        text = await page.evaluate("document.body?.innerText || ''")
                                        if len(text.strip()) > 100:
                                            print("   ✅ Conteúdo carregado/verificado.")
                                            break
                                    else:
                                        if attempt % 15 == 0:
                                            print(f"   ⏳ [Ação Necessária] Barreira Cloudflare detectada. Resolva o desafio no navegador...")
                                except Exception as e:
                                    # Se a página foi fechada ou algo assim
                                    if "closed" in str(e).lower():
                                        raise e
                                    pass
                                await asyncio.sleep(1)
                            
                            await asyncio.sleep(2.0)
                            raw_html = await page.content()
                            
                            # Processamento com Crawl4AI
                            print(f"🔄 Processando conteúdo com Crawl4AI ({url})...")
                            
                            run_config = CrawlerRunConfig(
                                css_selector="body",
                                excluded_tags=["footer", "nav"],
                                excluded_selector=self.excluded_selector,
                                markdown_generator=DefaultMarkdownGenerator(
                                    options={"ignore_links": True, "skip_internal_links": True}
                                ),
                            )
                            
                            # IMPORTANTE: Usamos o crawler apenas para converter o HTML que JA TEMOS
                            result = await crawler.arun(url=f"raw://{raw_html}", config=run_config)
                            if result.success:
                                all_markdowns.append(result.markdown)
                            else:
                                print(f"❌ Erro no Crawl4AI: {result.error_message}")
                                
                        except Exception as e:
                            print(f"❌ Erro ao processar URL {url}: {e}")
                            if "closed" in str(e).lower():
                                # Se o browser morreu, tenta reabrir na próxima URL do loop via reconexão no topo
                                break
                
            except Exception as e:
                print(f"❌ Erro crítico na conexão com o navegador: {e}")
            
            finally:
                # Limpeza: Mata apenas a instância específica do navegador que abrimos
                print("\n🏁 Finalizando scraper e fechando janela...")
                try:
                    if 'browser' in locals() and browser:
                        await browser.close()
                except: pass

                try:
                    browser_proc.terminate()
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(browser_proc.pid)], capture_output=True)
                except Exception:
                    pass
        
        return "\n\n".join(all_markdowns)
    
# Interface de compatibilidade para o resto do projeto
def scrape_url(urls):
    scraper = ScraperCrawl4AI()
    return asyncio.run(scraper.scrape(urls))

if __name__ == "__main__":
    # Teste rápido e salvamento em arquivo para compatibilidade com o modo manual
    test_urls = [
        "https://taimanin.fandom.com",
    ]
    
    print("\n🚀 Iniciando modo manual do ScraperCrawl4AI...")
    resultado = scrape_url(test_urls)
    
    if resultado:
        output_file = "scraped_content.txt"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(resultado)
            print(f"\n✅ Sucesso! Conteúdo extraído e salvo em: {output_file}")
            print(f"Resumo: {resultado[:200]}...")
        except Exception as e:
            print(f"❌ Erro ao salvar arquivo: {e}")
    else:
        print("\n❌ Falha na extração.")
