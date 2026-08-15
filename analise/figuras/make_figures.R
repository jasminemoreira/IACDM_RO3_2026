# Figuras do paper da RO3 — ggplot2, PDF vetorial (cairo_pdf).
#
# NENHUM NÚMERO É DIGITADO AQUI. Tudo vem de ../saidas/figuras/*.csv, que o
# `analise/figuras.py` computa do corpus. Antes de rodar isto:
#
#     python3 analise/figuras.py --conferir
#     Rscript --vanilla analise/figuras/make_figures.R
#
# A ORDEM DAS LINHAS DO CSV É A ORDEM DO EIXO, e os rótulos de legenda já vêm
# montados com suas contagens. Este script não ordena, não rotula e não deriva —
# a única aritmética que ele faz é o ratio do painel (b), e é de propósito: é
# `observado / esperado`, computado onde é usado, com o `esperado` em precisão
# plena. Dividir pelos 0,21 / 0,47 / 0,12 arredondados da tabela publicada erra o
# ratio em até meia unidade, porque o denominador tem duas casas decimais.
#
# Saída: $RO3_FIG_OUT, ou ../saidas/figuras se a variável não estiver definida.
# Para regenerar direto na pasta do paper:  RO3_FIG_OUT=/caminho/paper Rscript ...

if (nzchar(Sys.getenv("USERPROFILE"))) {                    # Windows: R do usuário
  lib <- file.path(Sys.getenv("USERPROFILE"), "Documents", "R", "win-library", "4.5")
  if (dir.exists(lib)) .libPaths(lib)
}
library(ggplot2)

aqui <- tryCatch(dirname(normalizePath(sub("^--file=", "", grep("^--file=",
          commandArgs(FALSE), value = TRUE)[1]))), error = function(e) ".")
dados <- file.path(aqui, "..", "saidas", "figuras")
saida <- Sys.getenv("RO3_FIG_OUT", unset = dados)
dir.create(saida, showWarnings = FALSE, recursive = TRUE)

ler <- function(nome) {
  caminho <- file.path(dados, nome)
  if (!file.exists(caminho))
    stop("falta ", caminho, " — rode `python3 analise/figuras.py` primeiro.",
         call. = FALSE)
  read.csv(caminho, check.names = FALSE, encoding = "UTF-8")
}
# a ordem de aparição no CSV é a ordem pretendida; de baixo para cima no eixo y
niveis <- function(x) factor(x, levels = unique(x))
niveis_y <- function(x) factor(x, levels = rev(unique(x)))
# Os limites e marcas de eixo abaixo são os do script original, ajustados à mão.
# São cosmética, não dado — ficam como estão para que uma figura cujos NÚMEROS não
# mudaram saia byte a byte igual à que está no paper. `teto` é só trava: se o dado
# passar do limite herdado, o eixo cresce em vez de cortar a barra em silêncio.
teto <- function(v, base) max(base, max(v) * 1.07)

# ---- paleta (validada com o validador de seis checagens do dataviz) ----
ramp   <- c("#86b6ef", "#5598e7", "#2a78d6", "#104281")  # ordinal, claro -> escuro
blue   <- "#2a78d6"
red    <- "#e34948"
ink    <- "#0b0b0b"
muted  <- "#898781"
grid   <- "#e1e0d9"
baseln <- "#c3c2b7"

theme_paper <- function(base = 10) {
  theme_minimal(base_size = base) +
    theme(
      text             = element_text(colour = ink),
      axis.text        = element_text(colour = ink, size = base - 1),
      axis.title       = element_text(colour = muted, size = base - 1),
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(colour = grid, linewidth = 0.3),
      legend.title     = element_blank(),
      legend.text      = element_text(size = base - 1),
      plot.title       = element_text(size = base - 1, hjust = 0.5, colour = ink),
      plot.margin      = margin(4, 8, 4, 4)
    )
}

salvar <- function(p, nome, ...) {
  ggsave(file.path(saida, nome), p, device = cairo_pdf, ...)
  cat("escrito ", file.path(saida, nome), "\n", sep = "")
}

# =====================================================================
# Figura 1 — contribuição exclusiva por lente sob quatro clusterizações
# =====================================================================
rob  <- ler("fig-robustness.csv")
nota <- ler("fig-annotations.csv")
rob$lens       <- niveis_y(rob$lens)
rob$clustering <- niveis(rob$clustering)

p1 <- ggplot(rob, aes(x = value, y = lens, colour = clustering, shape = clustering)) +
  geom_point(size = 2.1, stroke = 0.9, position = position_dodge(width = 0.72)) +
  scale_colour_manual(values = ramp) +
  scale_shape_manual(values = c(16, 15, 17, 18)) +
  scale_x_continuous(limits = c(0, teto(rob$value, 105)), breaks = seq(0, 100, 25),
                     expand = expansion(mult = c(0.005, 0.02))) +
  annotate("text", x = 22, y = levels(rob$lens)[1],
           hjust = 0, vjust = 0.4, colour = muted, size = 2.9,
           label = nota$text[nota$key == "robustness_minimum"]) +
  labs(x = "Exclusive contribution (defects in which the lens is the sole participant)",
       y = NULL) +
  theme_paper() +
  theme(panel.grid.major.y = element_blank(),
        legend.position = "inside",
        legend.position.inside = c(0.79, 0.20),
        legend.key.spacing.y = unit(1, "pt"))

salvar(p1, "fig-robustness.pdf", width = 6.3, height = 6.6)

# =====================================================================
# Figura 2 — divergências de ativação por lente, com direção
# =====================================================================
dv <- ler("fig-divergences.csv")
dv$lens      <- niveis_y(dv$lens)
dv$direction <- niveis(dv$direction)

p2 <- ggplot(dv, aes(x = value, y = lens, fill = direction)) +
  geom_col(width = 0.62) +
  geom_vline(xintercept = 0, colour = baseln, linewidth = 0.5) +
  geom_text(aes(label = abs(value), hjust = ifelse(value < 0, 1.4, -0.6)),
            colour = ink, size = 3.0) +
  scale_fill_manual(values = c(blue, red)) +
  scale_x_continuous(limits = c(-teto(-dv$value, 13), teto(dv$value, 7)),
                     breaks = c(-10, -5, 0, 5), labels = c("10", "5", "0", "5")) +
  labs(x = "Divergent project-lens decisions (summed over three estimators)",
       y = NULL) +
  guides(fill = guide_legend(ncol = 1)) +
  theme_paper() +
  theme(panel.grid.major.y = element_blank(), legend.position = "bottom")

salvar(p2, "fig-divergences.pdf", width = 6.0, height = 4.0)

# =====================================================================
# Figura 3 — marcação de duplicatas: (a) taxas, (b) concordância vs acaso
# =====================================================================
rates <- ler("fig-kappa-rates.csv")
rates$evaluator <- niveis_y(rates$evaluator)

p3a <- ggplot(rates, aes(x = marked_pairs, y = evaluator)) +
  geom_col(fill = blue, width = 0.6) +
  geom_text(aes(label = marked_pairs), hjust = -0.25, colour = ink, size = 3.0) +
  scale_x_continuous(limits = c(0, teto(rates$marked_pairs, 405)),
                     breaks = seq(0, 400, 100)) +
  labs(x = NULL, y = NULL, title = "(a) Marked pairs per marker") +
  theme_paper() +
  theme(panel.grid.major.y = element_blank())

salvar(p3a, "fig-kappa-rates.pdf", width = 3.0, height = 2.9)

chance <- ler("fig-kappa-chance.csv")
chance$pair <- niveis_y(chance$pair)
# a ÚNICA conta deste script — ver o cabeçalho
chance$ratio <- chance$observed / chance$expected

p3b <- ggplot(chance, aes(x = ratio, y = pair)) +
  geom_col(fill = blue, width = 0.6) +
  geom_vline(xintercept = 1, colour = muted, linetype = "dashed", linewidth = 0.4) +
  geom_text(aes(label = sprintf("κ = %.3f", kappa)),
            hjust = -0.12, colour = muted, size = 2.9) +
  scale_x_continuous(limits = c(0, teto(chance$ratio, 235)), breaks = seq(0, 200, 50)) +
  labs(x = NULL, y = NULL, title = "(b) Observed co-marks ÷ expected by chance") +
  theme_paper() +
  theme(panel.grid.major.y = element_blank())

salvar(p3b, "fig-kappa-chance.pdf", width = 3.9, height = 2.9)
