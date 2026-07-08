##############################################################################
# Adaptive Rejection Sampling (ARS)
# Reference: Gilks, W. R., & Wild, P. (1992). Adaptive rejection sampling for
#            Gibbs sampling. JRSS-C, 41(2), 337-348.
#
# Modules:
#   ars              - Main sampling function
#   startingpoints   - Find initial abscissae
#   createLowHull    - Construct piecewise-linear lower hull
#   createUpHull     - Construct piecewise-linear upper hull (envelope)
#   sampleUp         - Sample a candidate from the upper hull
#   evalSampPt       - Evaluate candidate on upper and lower hulls
#   rejectiontest    - Squeeze/acceptance/rejection test
#   test             - Formal test suite
##############################################################################

## ---------------------------------------------------------------------------
## startingpoints: Determine initial abscissae for the ARS algorithm
##
## Args:
##   D: Domain vector c(lower, upper)
##   h: Log-density function
##   A: Optional user-specified left starting point
##   B: Optional user-specified right starting point
## Returns:
##   T: Numeric vector of two starting abscissae
## ---------------------------------------------------------------------------
startingpoints <- function(D, h, A, B) {
  D[1][is.na(D[1])] <- -Inf
  D[2][is.na(D[2])] <- Inf

  if (D[1] == -Inf && D[2] == Inf) {
    if (is.numeric(A) && is.numeric(B)) {
      a <- A; b <- B
    } else {
      a <- -4; b <- 4
    }
    ap <- diag(attr(numericDeriv(quote(h(a)), "a"), "gradient"))
    bp <- diag(attr(numericDeriv(quote(h(b)), "b"), "gradient"))
    if (ap > 0 && bp < 0) {
      T <- c(a, b)
    } else if (ap > 0 && bp >= 0) {
      stop("No points to the right of the mode")
    } else if (ap <= 0 && bp < 0) {
      stop("No points to the left of the mode")
    } else {
      stop("Please give a valid domain for g(x)! Please try again!")
    }
  } else if (D[1] == -Inf) {
    a <- -4; b <- D[2]
    if (a >= b) a <- 2 * b
    T <- c(a, b)
  } else if (D[2] == Inf) {
    if (is.numeric(A)) a <- A else a <- D[1]
    if (is.numeric(B)) b <- B else b <- 4
    if (a >= b) b <- 2 * a
    T <- c(a, b)
  } else {
    if (is.numeric(A) && is.numeric(B)) {
      a <- A; b <- B
    } else {
      a <- D[1] + 0.003; b <- D[2] - 0.003
    }
    T <- c(a, b)
  }
  return(T)
}

## ---------------------------------------------------------------------------
## createLowHull: Build piecewise-linear lower hull (sandwiching function)
## ---------------------------------------------------------------------------
createLowHull <- function(T, h, D) {
  m <- (h(T[-1]) - h(T[-length(T)])) / (T[-1] - T[-length(T)])
  b <- (T[-1] * h(T[-length(T)]) - T[-length(T)] * h(T[-1])) / (T[-1] - T[-length(T)])
  left <- T[-length(T)]
  right <- T[-1]
  LowerBound <- data.frame(cbind(m, b, left, right))
  colnames(LowerBound) <- c("m", "b", "left", "right")
  return(LowerBound)
}

## ---------------------------------------------------------------------------
## createUpHull: Build piecewise-linear upper hull (envelope function)
##               Also checks log-concavity (slopes must be decreasing)
## ---------------------------------------------------------------------------
createUpHull <- function(T, h, D) {
  x <- T
  m <- diag(attr(numericDeriv(quote(h(x)), "x"), "gradient"))
  # Log-concavity check: slopes of log-density must be strictly decreasing
  if (length(m) > 1 && any(diff(m) > 1e-10)) {
    stop("Density is not log-concave on the specified domain")
  }
  b <- h(T) - m * T
  z <- (b[-1] - b[-length(b)]) / (m[-length(m)] - m[-1])
  prob0 <- exp(b) / m * (exp(m * c(z, D[2])) - exp(m * c(D[1], z)))
  prob <- prob0 / sum(prob0)
  prob[is.nan(prob)] <- 1
  left <- c(D[1], z)
  right <- c(z, D[2])
  if (length(m) == 2 && m[1] == m[2]) {
    UpBound <- data.frame(cbind(m[1], b[1], prob[1], left[1], right[2]))
  } else {
    UpBound <- data.frame(cbind(m, b, prob, left, right))
  }
  colnames(UpBound) <- c("m", "b", "prob", "left", "right")
  return(UpBound)
}

## ---------------------------------------------------------------------------
## sampleUp: Draw a candidate from the piecewise-exponential upper hull
## ---------------------------------------------------------------------------
sampleUp <- function(UpperHull) {
  emp.cdf <- cumsum(UpperHull$prob)
  invalid <- TRUE
  while (invalid) {
    u <- runif(1)
    ind <- min(which(u < emp.cdf, arr.ind = TRUE))
    u <- runif(1)
    m <- UpperHull$m[ind]
    b <- UpperHull$b[ind]
    left <- UpperHull$left[ind]
    right <- UpperHull$right[ind]
    x <- log(u * (exp(m * right) - exp(m * left)) + exp(m * left)) / m
    if (!is.infinite(x) && !is.nan(x) && !is.na(x)) {
      if (x >= UpperHull$left[1] && x <= UpperHull$right[nrow(UpperHull)]) {
        invalid <- FALSE
      }
    }
  }
  return(x)
}

## ---------------------------------------------------------------------------
## evalSampPt: Evaluate a candidate on upper and lower hulls
## ---------------------------------------------------------------------------
evalSampPt <- function(x, UpHull, LowHull) {
  if (x < min(LowHull$left) || x > max(LowHull$right)) {
    lEval <- -Inf
  } else {
    ind <- which(x >= LowHull$left & x <= LowHull$right, arr.ind = TRUE)
    lEval <- LowHull$m[ind] * x + LowHull$b[ind]
  }
  indR <- which(x >= UpHull$left & x <= UpHull$right, arr.ind = TRUE)
  uEval <- UpHull$m[indR] * x + UpHull$b[indR]
  return(c(lEval, uEval))
}

## ---------------------------------------------------------------------------
## rejectiontest: Squeeze / acceptance / rejection test (Gilks & Wild 1992)
## ---------------------------------------------------------------------------
rejectiontest <- function(x_star, w, l_k, u_k, h) {
  if (w <= exp(l_k - u_k)) {
    A <- TRUE; Up <- FALSE; logconcave <- TRUE
  } else if (w <= exp(h(x_star) - u_k)) {
    A <- TRUE; Up <- TRUE; logconcave <- (l_k <= u_k)
  } else {
    A <- FALSE; Up <- TRUE; logconcave <- (l_k <= u_k)
  }
  return(c(A, Up, logconcave))
}

## ---------------------------------------------------------------------------
## ars: Adaptive Rejection Sampling — main function
##
## Generates n independent samples from a univariate log-concave density
## using the ARS algorithm (Gilks & Wild, 1992).
##
## Args:
##   g: Target density function (vectorized, e.g. dnorm, dexp)
##   D: Domain vector c(lower, upper). Use NA, -Inf, or Inf for unbounded.
##   a: Optional left starting abscissa (default NA = auto-select).
##   b: Optional right starting abscissa (default NA = auto-select).
##   n: Number of samples to draw (positive integer).
##
## Returns:
##   Numeric vector of n samples from the target density.
##
## Errors:
##   - n <= 0 or non-integer  -> "Number of samples must be positive"
##   - Invalid D  -> "Domain D must be a vector of length 2"
##   - Non-log-concave density  -> detected via createUpHull slopes check
##   - Invalid starting points or density evaluations
## ---------------------------------------------------------------------------
ars <- function(g, D = c(NA, NA), a = NA, b = NA, n = 1) {

  # -------- Input validation --------
  if (!is.numeric(n) || length(n) != 1 || is.na(n) || n <= 0 || n != floor(n)) {
    stop("Number of samples must be a positive integer")
  }
  n <- as.integer(n)

  if (!is.vector(D) || length(D) != 2) {
    stop("Domain D must be a vector of length 2 (lower, upper)")
  }
  D_res <- D
  if (is.na(D_res[1])) D_res[1] <- -Inf
  if (is.na(D_res[2])) D_res[2] <- Inf
  if (is.finite(D_res[1]) && is.finite(D_res[2]) && D_res[1] >= D_res[2]) {
    stop("Invalid domain: lower bound must be less than upper bound")
  }

  if (!is.function(g)) {
    stop("g must be a function that computes the (possibly unnormalized) density")
  }

  # Quick sanity check: g should produce positive values
  t_lo <- if (is.finite(D_res[1])) D_res[1] + 0.1 else -10
  t_hi <- if (is.finite(D_res[2])) D_res[2] - 0.1 else 10
  t_pts <- seq(max(t_lo, -50), min(t_hi, 50), length.out = 100)
  gv <- tryCatch(g(t_pts), error = function(e) NA)
  if (all(is.na(gv)) || all(gv <= 0, na.rm = TRUE)) {
    stop("Density function g does not produce positive values in the domain")
  }

  if ((is.na(a) && !is.na(b)) || (!is.na(a) && is.na(b))) {
    stop("Please specify both a and b, or neither (both NA)")
  }

  h <- function(x) log(g(x))
  samp <- numeric(n)

  # -------- Starting points --------
  T_k <- startingpoints(D, h, a, b)
  if (T_k[1] < D_res[1] || T_k[2] > D_res[2]) {
    stop("At least one starting point lies outside the domain")
  }
  if (g(T_k[1]) <= 0 || g(T_k[2]) <= 0) {
    stop("Density is zero or negative at the starting points")
  }

  # -------- Initial hulls --------
  Low <- createLowHull(T_k, h, D_res)
  Up <- createUpHull(T_k, h, D_res)

  # -------- Main sampling loop --------
  k <- 0
  while (k < n) {
    x.star <- sampleUp(Up)
    u <- runif(1)
    evals <- evalSampPt(x.star, Up, Low)
    test_result <- rejectiontest(x.star, u, evals[1], evals[2], h)
    A <- test_result[1]
    Up_flag <- test_result[2]
    is_logconcave <- test_result[3]

    if (!is_logconcave) {
      stop("Non-log-concave density detected. ",
           "ARS requires a log-concave target density.")
    }

    if (A) {
      k <- k + 1
      samp[k] <- x.star
      if (Up_flag) T_k <- sort(c(T_k, x.star))
    } else {
      T_k <- sort(c(T_k, x.star))
      Up <- try(createUpHull(T_k, h, D_res), silent = TRUE)
      if (inherits(Up, "try-error")) {
        stop("Failed to update upper hull. ",
             "Adjust starting points or domain.")
      }
      Low <- createLowHull(T_k, h, D_res)
    }
  }

  return(samp)
}

## ---------------------------------------------------------------------------
## test: Formal test suite for the Adaptive Rejection Sampler
##
## Runs 11 tests covering:
##   - Sampling from standard distributions (normal, exponential, gamma, beta)
##   - Input validation (negative n, invalid domain, bad starting points)
##   - Non-log-concave density detection
##   - Auxiliary function correctness (createLowHull, createUpHull, startingpoints)
##
## Output is printed to stdout in a clear, interpretable format with
## "TEST_NAME: PASS" or "TEST_NAME: FAIL" for each test, plus summary.
## ---------------------------------------------------------------------------
test <- function() {
  cat("================================================================\n")
  cat("  Adaptive Rejection Sampler - Formal Test Suite\n")
  cat("================================================================\n\n")

  set.seed(42)
  n_pass <- 0
  n_total <- 11

  # ---- Test 1: Standard Normal ----
  cat("[TEST 1] Standard Normal Distribution (n = 2000)\n")
  cat("         Target: N(0,1), domain = (-Inf, Inf)\n")
  tryCatch({
    s1 <- ars(dnorm, c(-Inf, Inf), n = 2000)
    m1 <- mean(s1); s1sd <- sd(s1)
    pass <- abs(m1) < 0.10 && abs(s1sd - 1) < 0.10
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         Mean: %.4f (expected 0.0000), SD: %.4f (expected 1.0000)\n", m1, s1sd))
    cat(sprintf("         Normal Distribution: %s\n\n", ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         Normal Distribution: FAIL (%s)\n\n", e$message)))

  # ---- Test 2: Exponential ----
  cat("[TEST 2] Exponential Distribution (rate=1, n = 2000)\n")
  cat("         Target: Exp(1), domain = (0.01, Inf)\n")
  tryCatch({
    d2 <- function(x) dexp(x, rate = 1)
    s2 <- ars(d2, c(0.01, Inf), n = 2000)
    m2 <- mean(s2); s2sd <- sd(s2)
    pass <- abs(m2 - 1) < 0.10 && abs(s2sd - 1) < 0.10
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         Mean: %.4f (expected 1.0000), SD: %.4f (expected 1.0000)\n", m2, s2sd))
    cat(sprintf("         Exponential Distribution: %s\n\n", ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         Exponential Distribution: FAIL (%s)\n\n", e$message)))

  # ---- Test 3: Gamma ----
  cat("[TEST 3] Gamma Distribution (shape=2, rate=1, n = 2000)\n")
  cat("         Target: Gamma(2,1), domain = (0.01, Inf)\n")
  tryCatch({
    d3 <- function(x) dgamma(x, shape = 2, rate = 1)
    s3 <- ars(d3, c(0.01, Inf), n = 2000)
    m3 <- mean(s3); s3sd <- sd(s3)
    pass <- abs(m3 - 2) < 0.20 && abs(s3sd - sqrt(2)) < 0.20
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         Mean: %.4f (expected 2.0000), SD: %.4f (expected 1.4142)\n", m3, s3sd))
    cat(sprintf("         Gamma Distribution: %s\n\n", ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         Gamma Distribution: FAIL (%s)\n\n", e$message)))

  # ---- Test 4: Beta ----
  cat("[TEST 4] Beta Distribution (shape1=2, shape2=2, n = 2000)\n")
  cat("         Target: Beta(2,2), domain = (0.001, 0.999)\n")
  tryCatch({
    d4 <- function(x) dbeta(x, shape1 = 2, shape2 = 2)
    s4 <- ars(d4, c(0.001, 0.999), n = 2000)
    m4 <- mean(s4); s4sd <- sd(s4)
    pass <- abs(m4 - 0.5) < 0.05 && abs(s4sd - 0.2236) < 0.05
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         Mean: %.4f (expected 0.5000), SD: %.4f (expected 0.2236)\n", m4, s4sd))
    cat(sprintf("         Beta Distribution: %s\n\n", ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         Beta Distribution: FAIL (%s)\n\n", e$message)))

  # ---- Test 5: Input validation - negative n ----
  cat("[TEST 5] Input validation -- negative n\n")
  pass <- tryCatch({ ars(dnorm, c(-5, 5), n = -1); FALSE }, error = function(e) TRUE)
  if (pass) n_pass <- n_pass + 1
  cat(sprintf("         Negative n properly rejected: %s\n\n", ifelse(pass, "PASS", "FAIL")))

  # ---- Test 6: Input validation - invalid domain ----
  cat("[TEST 6] Input validation -- invalid domain (lower >= upper)\n")
  pass <- tryCatch({ ars(dnorm, c(5, -5), n = 10); FALSE }, error = function(e) TRUE)
  if (pass) n_pass <- n_pass + 1
  cat(sprintf("         Invalid domain properly rejected: %s\n\n", ifelse(pass, "PASS", "FAIL")))

  # ---- Test 7: Input validation - density zero at starting points ----
  cat("[TEST 7] Input validation -- density zero at starting points\n")
  pass <- tryCatch({
    bad <- function(x) ifelse(abs(x) < 1, 1, 0)
    ars(bad, c(-Inf, Inf), a = -10, b = 10, n = 10)
    FALSE
  }, error = function(e) TRUE)
  if (pass) n_pass <- n_pass + 1
  cat(sprintf("         Invalid starting points properly rejected: %s\n\n", ifelse(pass, "PASS", "FAIL")))

  # ---- Test 8: Non-log-concave density ----
  cat("[TEST 8] Non-log-concave density detection\n")
  cat("         Target: t(1) (Cauchy) -- not log-concave\n")
  pass <- tryCatch({
    nlc <- function(x) dt(x, df = 1)
    ars(nlc, c(-Inf, Inf), n = 100)
    FALSE
  }, error = function(e) TRUE)
  if (pass) n_pass <- n_pass + 1
  cat(sprintf("         Non-log-concave density properly detected: %s\n\n", ifelse(pass, "PASS", "FAIL")))

  # ---- Test 9: Auxiliary function - createLowHull ----
  cat("[TEST 9] Auxiliary function -- createLowHull structure\n")
  tryCatch({
    h9 <- function(x) log(dnorm(x))
    low9 <- createLowHull(c(-2, 0, 2), h9, c(-Inf, Inf))
    pass <- is.data.frame(low9) && all(c("m","b","left","right") %in% names(low9)) && nrow(low9) == 2
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         createLowHull: %s\n\n", ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         createLowHull: FAIL (%s)\n\n", e$message)))

  # ---- Test 10: Auxiliary function - createUpHull ----
  cat("[TEST 10] Auxiliary function -- createUpHull structure\n")
  tryCatch({
    h10 <- function(x) log(dnorm(x))
    up10 <- createUpHull(c(-2, 0, 2), h10, c(-Inf, Inf))
    pass <- is.data.frame(up10) && all(c("m","b","prob","left","right") %in% names(up10))
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         createUpHull: %s\n\n", ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         createUpHull: FAIL (%s)\n\n", e$message)))

  # ---- Test 11: Starting points ----
  cat("[TEST 11] Starting points for unbounded domain\n")
  tryCatch({
    h11 <- function(x) log(dnorm(x))
    sp11 <- startingpoints(c(-Inf, Inf), h11, NA, NA)
    pass <- length(sp11) == 2 && sp11[1] < sp11[2]
    if (pass) n_pass <- n_pass + 1
    cat(sprintf("         Starting points: [%.2f, %.2f] %s\n\n", sp11[1], sp11[2], ifelse(pass, "PASS", "FAIL")))
  }, error = function(e) cat(sprintf("         Starting points: FAIL (%s)\n\n", e$message)))

  # ---- Summary ----
  cat("================================================================\n")
  cat(sprintf("  RESULTS: %d / %d tests passed\n", n_pass, n_total))
  cat("================================================================\n")
  cat(sprintf("  OVERALL: %s\n", ifelse(n_pass == n_total, "PASS", "FAIL")))
  cat("================================================================\n")

  invisible(list(passed = n_pass, total = n_total))
}
