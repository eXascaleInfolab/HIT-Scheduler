library(scales)
library(ggplot2)
data <- read.csv(file = 'throughput_5cent_price_3months_correct.txt', header=T, sep='\t')
attach(data)
ggplot(data.frame(x=hits, y=throughput), aes(x = x, y = y)) +  
   geom_point(col=gid) + stat_smooth(method = "lm") +
   stat_function(fun = function(x) 0.05*x, geom='line',colour = 'red') +
   coord_trans(xtrans = 'log10',ytrans = 'log10', limx = c(1,100000), limy =c(0.000001,10000)) +
  annotation_logticks(scaled=FALSE) +
   scale_x_continuous(breaks = trans_breaks("log10", function(x) 10^x),
                labels = trans_format("log10", math_format(10^.x))) +
  scale_y_continuous(breaks = trans_breaks("log10", function(x) 10^x),
                     labels = trans_format("log10", math_format(10^.x)))